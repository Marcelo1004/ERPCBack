# apps/productos/views.py

from rest_framework import viewsets, permissions, generics
from rest_framework.exceptions import PermissionDenied
from rest_framework import filters
import django_filters.rest_framework
from rest_framework.response import Response  # Importar Response
from rest_framework import status  # Importar status

# Importaciones para DemandaPredictivaView
from django.db.models import Sum, Avg, Count, F, Q, Value  # Asegurarse de que Value está aquí
from django.db.models.functions import Coalesce, Concat  # Asegurarse de que Concat y Coalesce están aquí
from django.utils import timezone
from datetime import datetime, timedelta
import random  # Para simular la aleatoriedad del modelo predictivo

from apps.empresas.models import Empresa
from .models import Producto
from .serializers import ProductoSerializer, ProductoListSerializer  # Asegurarse de importar ProductoListSerializer
from .filters import ProductoFilter


class ProductoPermission(permissions.BasePermission):
    """
    Permiso personalizado para la gestión de Productos (uso administrativo).
    - Superusuarios: Acceso total a todos los productos.
    - Administradores de Empresa: Acceso total solo a productos de SU propia empresa.
    - Otros usuarios autenticados (CLIENTE, EMPLEADO): Solo lectura de productos de SU propia empresa.
    """

    def has_permission(self, request, view):
        if not request.user or request.user.is_anonymous:
            raise PermissionDenied("Debe estar autenticado para acceder a los productos.")

        if request.user.is_superuser:
            return True

        if not hasattr(request.user, 'role') or request.user.role is None or \
                not hasattr(request.user, 'empresa') or request.user.empresa is None:
            raise PermissionDenied("Su cuenta no tiene un rol o empresa válidos asignados.")

        user_role_name = request.user.role.name

        if user_role_name == 'Administrador':
            return True

        if user_role_name in ['Cliente', 'Empleado'] and request.method in permissions.SAFE_METHODS:
            return True

        return False

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        if request.user.is_authenticated and \
                hasattr(request.user, 'empresa') and request.user.empresa is not None and \
                request.user.empresa == obj.empresa:

            if request.method in permissions.SAFE_METHODS:
                return True

            if hasattr(request.user,
                       'role') and request.user.role is not None and request.user.role.name == 'Administrador':
                return True

        return False


class ProductoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para la gestión de Productos (parte administrativa).
    Proporciona acciones de listado, creación, recuperación, actualización y eliminación,
    con soporte para filtrado y búsqueda.
    """
    serializer_class = ProductoSerializer
    permission_classes = [ProductoPermission]  # Asegúrate que tu permiso personalizado está activo aquí

    filter_backends = [filters.SearchFilter, django_filters.rest_framework.DjangoFilterBackend]
    filterset_class = ProductoFilter
    search_fields = [
        'nombre',
        'descripcion',
        'categoria__nombre',
        'almacen__nombre',
        'almacen__sucursal__nombre',
    ]
    # --- Importante: Define un queryset por defecto para que el router lo registre ---
    queryset = Producto.objects.all()

    # --- Consolidación del get_queryset ---
    def get_queryset(self):
        print("\n--- DEBUG: get_queryset de ProductoViewSet llamado ---")

        if getattr(self, 'swagger_fake_view', False):
            print("--- DEBUG: Modo Swagger_fake_view activado, retornando queryset vacío. ---")
            return Producto.objects.none()

        user = self.request.user
        if user.is_superuser:
            # Superusuario puede ver todos los productos (activos o inactivos)
            return Producto.objects.all().order_by('nombre')
        elif user.is_authenticated and hasattr(user, 'empresa') and user.empresa:
            # Usuarios autenticados con una empresa asignada:
            # Solo pueden ver y operar con productos de SU PROPIA empresa y que estén activos
            # (asumiendo que 'is_active' ya existe en tu modelo Producto)
            return Producto.objects.filter(empresa=user.empresa, is_active=True).order_by('nombre')

        # Si el usuario no es superusuario, no está autenticado, o no tiene empresa asignada,
        # no debe ver ningún producto en el listado del ViewSet administrativo.
        return Producto.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_superuser:
            if not (hasattr(user, 'empresa') and user.empresa):
                raise PermissionDenied("No estás asociado a ninguna empresa para crear productos.")
            serializer.save(empresa=user.empresa)
        else:
            serializer.save()

    def get_serializer_class(self):
        serializer_class = super().get_serializer_class()
        print(f"\n--- DEBUG: ProductoViewSet está usando el serializer: {serializer_class.__name__} ---")
        return serializer_class


# --- NUEVAS VISTAS PARA EL MARKETPLACE PÚBLICO ---

class ProductoListView(generics.ListAPIView):
    """
    Vista para listar productos de una empresa específica en el marketplace público.
    No requiere autenticación.
    """
    serializer_class = ProductoListSerializer  # Usamos el serializer más ligero para la lista
    permission_classes = []  # Acceso público

    def get_queryset(self):
        empresa_id = self.kwargs['empresa_id']  # Obtiene el ID de la empresa de la URL
        try:
            # Asegúrate de que la empresa exista y esté activa para listar sus productos
            empresa = Empresa.objects.get(id=empresa_id, is_active=True)
        except Empresa.DoesNotExist:
            return Producto.objects.none()  # Si la empresa no existe o no está activa, no hay productos que mostrar

        # Filtra productos por la empresa y solo los activos (asumiendo 'is_active' en Producto)
        return Producto.objects.filter(empresa=empresa, is_active=True).order_by('nombre')


class ProductoDetailView(generics.RetrieveAPIView):
    """
    Vista para ver detalles de un producto individual en el marketplace público.
    No requiere autenticación.
    """
    serializer_class = ProductoSerializer  # Usamos el serializer completo para el detalle
    lookup_field = 'pk'  # Campo para buscar por ID en la URL
    permission_classes = []  # Acceso público

    def get_queryset(self):
        # Filtra productos activos de empresas activas (asumiendo 'is_active' en Producto)
        return Producto.objects.filter(is_active=True, empresa__is_active=True)


# --- Endpoint para el Modelo Predictivo de Demanda (SIMPLIFICADO) ---
class DemandaPredictivaView(generics.GenericAPIView):
    """
    Vista para obtener una predicción de demanda simulada para un producto.
    """
    permission_classes = []  # Público para esta demo

    def get(self, request, pk, *args, **kwargs):
        # El 'pk' será el ID del producto para el cual queremos la predicción
        try:
            producto = Producto.objects.get(pk=pk, is_active=True)  # Solo productos activos
        except Producto.DoesNotExist:
            return Response({"error": "Producto no encontrado o inactivo."}, status=status.HTTP_404_NOT_FOUND)

        # --- SIMULACIÓN DEL MODELO PREDICTIVO DE DEMANDA ---
        # COMENTARIO CLAVE PARA LA EXPLICACIÓN: Aquí es donde iría tu lógica
        # del modelo predictivo real (IA). Para esta demo rápida, simulamos:

        # Una "demanda base" que podría ser, por ejemplo, el 10-30% del stock actual.
        base_demanda_simulada = producto.stock * random.uniform(0.1, 0.3)

        # Un factor aleatorio que añade variabilidad. Simula picos o caídas inesperadas.
        factor_variabilidad = random.uniform(0.8, 1.2)

        # Cálculo final de la predicción, redondeado a un número entero de unidades.
        prediccion_demanda = round(base_demanda_simulada * factor_variabilidad)

        # Asegurarse de que la predicción nunca sea un número negativo (la demanda siempre es >= 0)
        prediccion_demanda = max(0, prediccion_demanda)

        # Simular una "confianza" en la predicción.
        confianza_prediccion = random.uniform(0.7, 0.95)

        return Response({
            "producto_id": producto.id,
            "producto_nombre": producto.nombre,
            "prediccion_demanda_proximos_dias": prediccion_demanda,
            "confianza_prediccion": round(confianza_prediccion * 100, 2),  # Se muestra en porcentaje
            "fecha_prediccion": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
            "explicacion_simplificada": "Esta predicción de demanda se genera simulando un análisis de datos históricos de ventas y aplicando factores de variabilidad aleatorios. Aunque es una simulación, representa cómo un modelo de IA real optimizaría la gestión de tu inventario.",
            "beneficio_erp": "La predicción de demanda te permite anticiparte a las necesidades del mercado, optimizar tus niveles de stock, reducir costos por exceso de inventario y evitar la pérdida de ventas por falta de existencias."
        }, status=status.HTTP_200_OK)