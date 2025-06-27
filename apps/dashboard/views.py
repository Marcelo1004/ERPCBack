# dashboard/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Count, Sum, F, ExpressionWrapper, DecimalField, Q
from django.db.models.functions import TruncMonth
from rest_framework.permissions import IsAuthenticated, BasePermission
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import models  # Asegúrate de importar models si usas F, Q, etc.

# Importa tus modelos. ¡ASEGÚRATE DE QUE ESTAS RUTAS SEAN CORRECTAS!
from apps.usuarios.models import CustomUser
from apps.empresas.models import Empresa
from apps.sucursales.models import Sucursal
from apps.almacenes.models import Almacen
from apps.categorias.models import Categoria
from apps.productos.models import Producto
from apps.suscripciones.models import Suscripcion
from apps.proveedores.models import Proveedor  # ¡NUEVO! Importamos el modelo Proveedor

# Importaciones de modelos de Ventas y DetalleVenta
from apps.ventas.models import Venta, DetalleVenta

# Asegúrate de que este serializer exista y esté definido correctamente
from .serializers import DashboardERPSerializer


class IsWorkerUser(BasePermission):
    """
    Permiso personalizado para permitir acceso a SuperUsuarios, Administrativos y Empleados.
    Los clientes no tienen acceso al dashboard.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        return user.role in ['ADMINISTRATIVO', 'EMPLEADO']


class DashboardERPView(APIView):
    permission_classes = [IsWorkerUser]

    def get(self, request):
        user = request.user

        dashboard_data = {
            'total_usuarios': 0,
            'total_sucursales': 0,
            'total_almacenes': 0,
            'total_categorias': 0,
            'total_productos': 0,
            'valor_total_inventario': '0.00',
            'productos_bajo_stock': [],
            'distribucion_suscripciones': [],
            'monthly_sales': [],
            'top_products': [],
            'category_distribution': [],
            'inventory_by_warehouse': [],
            'recent_activities': [],  # Aseguramos que esté aquí desde el inicio
            'total_empresas': 0,
            'total_proveedores': 0,  # ¡NUEVO! Inicializamos el total de proveedores
        }

        try:
            empresa_filter = Q()

            if not user.is_superuser:
                if hasattr(user, 'empresa') and user.empresa:
                    # DEBUG: Imprime la empresa asociada al usuario
                    print(
                        f"DEBUG: User '{user.email}' is associated with company: {user.empresa.nombre} (ID: {user.empresa.id})")
                    empresa_filter = Q(empresa=user.empresa)
                else:
                    # DEBUG: Imprime si el usuario no tiene empresa
                    print(f"DEBUG: Non-superuser '{user.email}' has no associated company or user.empresa is None.")
                    return Response(
                        {"message": "No hay datos de dashboard disponibles para su cuenta o empresa."},
                        status=status.HTTP_200_OK
                    )
            else:
                # DEBUG: Usuario superusuario
                print(f"DEBUG: User '{user.email}' is a Superuser.")

            # Aplicamos el filtro a todos los QuerySets
            user_qs = CustomUser.objects.filter(empresa_filter)
            empresa_qs = Empresa.objects.all() if user.is_superuser else Empresa.objects.filter(id=user.empresa.id)
            sucursal_qs = Sucursal.objects.filter(empresa_filter)
            almacen_qs = Almacen.objects.filter(empresa_filter)
            categoria_qs = Categoria.objects.filter(empresa_filter)
            producto_qs = Producto.objects.filter(empresa_filter)

            # DEBUG: Queryset de Proveedores ANTES de contar
            proveedor_qs = Proveedor.objects.filter(empresa_filter)
            print(f"DEBUG: Proveedor queryset filter applied: {empresa_filter}")
            print(f"DEBUG: Proveedores found by filter: {proveedor_qs.count()}")
            # DEBUG: Imprime los IDs y nombres de los proveedores encontrados
            print(f"DEBUG: Details of providers found: {list(proveedor_qs.values('id', 'nombre', 'empresa__nombre'))}")

            dashboard_data['total_proveedores'] = proveedor_qs.count()

            # Querysets para ventas, considerando la relación con la empresa
            venta_qs = Venta.objects.filter(empresa_filter)
            detalle_venta_qs = DetalleVenta.objects.filter(venta__in=venta_qs)

            # -----------------------------------------------------------
            # CÁLCULO DE MÉTRICAS
            # -----------------------------------------------------------

            # Métricas Core
            dashboard_data['total_usuarios'] = user_qs.count()
            dashboard_data['total_sucursales'] = sucursal_qs.count()
            dashboard_data['total_almacenes'] = almacen_qs.count()
            dashboard_data['total_categorias'] = categoria_qs.count()
            dashboard_data['total_productos'] = producto_qs.count()

            valor_inventario_agg = producto_qs.aggregate(
                total_valor=Sum(ExpressionWrapper(F('precio') * F('stock'),
                                                  output_field=DecimalField(max_digits=15, decimal_places=2)))
            )['total_valor']
            dashboard_data['valor_total_inventario'] = f"{valor_inventario_agg or 0.00:.2f}"

            productos_bajo_stock_qs = producto_qs.filter(stock__lt=10).values_list('nombre', flat=True)
            dashboard_data['productos_bajo_stock'] = list(productos_bajo_stock_qs)

            # Distribución de suscripciones (solo para superusuarios)
            if user.is_superuser:
                dashboard_data['total_empresas'] = Empresa.objects.count()
                suscripciones_dist = Empresa.objects.values(
                    plan_nombre=F('suscripcion__nombre')
                ).annotate(
                    cantidad_empresas=Count('id')
                ).order_by('plan_nombre')
                dashboard_data['distribucion_suscripciones'] = list(suscripciones_dist)
            else:
                dashboard_data['total_empresas'] = 0
                dashboard_data['distribucion_suscripciones'] = []

            # Ventas Mensuales
            monthly_sales_data = []
            today = timezone.now()
            start_date_for_charts = (today - timedelta(days=180)).replace(day=1, hour=0, minute=0, second=0,
                                                                          microsecond=0)

            monthly_sales_results = venta_qs.filter(
                fecha__gte=start_date_for_charts
            ).annotate(
                month_start=TruncMonth('fecha')
            ).values('month_start').annotate(
                total_ventas=Sum('monto_total')
            ).order_by('month_start')

            current_month_iterator = start_date_for_charts
            while current_month_iterator <= today:
                month_name = current_month_iterator.strftime('%b')

                sales_for_month = next((
                    item for item in monthly_sales_results
                    if item['month_start'].month == current_month_iterator.month and
                       item['month_start'].year == current_month_iterator.year
                ), None)

                monthly_sales_data.append({
                    'name': month_name,
                    'Ventas': float(sales_for_month['total_ventas']) if sales_for_month and sales_for_month[
                        'total_ventas'] is not None else 0.00
                })

                if current_month_iterator.month == 12:
                    current_month_iterator = current_month_iterator.replace(year=current_month_iterator.year + 1,
                                                                            month=1, day=1)
                else:
                    current_month_iterator = current_month_iterator.replace(month=current_month_iterator.month + 1,
                                                                            day=1)

            dashboard_data['monthly_sales'] = monthly_sales_data

            # Productos Más Vendidos
            top_products_data = []
            top_products_results = detalle_venta_qs.values(
                'producto__nombre'
            ).annotate(
                sales=Sum(F('cantidad') * F('precio_unitario'),
                          output_field=DecimalField(max_digits=15, decimal_places=2)),
                units=Sum('cantidad')
            ).order_by('-sales')[:5]

            for item in top_products_results:
                top_products_data.append({
                    'name': item['producto__nombre'],
                    'sales': float(item['sales'] or 0.00),
                    'units': item['units'] or 0
                })
            dashboard_data['top_products'] = top_products_data

            # Distribución por Categoría
            category_distribution_data = list(
                producto_qs.values(name=F('categoria__nombre')).annotate(
                    products_count=Count('id')
                ).order_by('name')
            )
            dashboard_data['category_distribution'] = [
                item for item in category_distribution_data if item['name'] is not None
            ]

            # Inventario por Almacén
            inventory_by_warehouse_data = list(
                almacen_qs.annotate(
                    total_value=Sum(F('productos__precio') * F('productos__stock'),
                                    output_field=DecimalField(max_digits=15, decimal_places=2)),
                    product_count=Count('productos__id', distinct=True)
                ).values('nombre', 'total_value', 'product_count')
            )
            dashboard_data['inventory_by_warehouse'] = []
            for item in inventory_by_warehouse_data:
                if item['nombre'] is not None and (
                        item['total_value'] is not None or item['product_count'] is not None):
                    dashboard_data['inventory_by_warehouse'].append({
                        'name': item['nombre'],
                        'total_value': float(item['total_value'] or 0.00),
                        'product_count': item['product_count'] or 0
                    })

            # Actividades Recientes
            recent_activities_list = []

            # Actividades: Nuevas Ventas/Pedidos
            for venta in venta_qs.order_by('-fecha')[:5]:
                user_name = venta.usuario.first_name if venta.usuario and venta.usuario.first_name else 'Usuario Desconocido'
                recent_activities_list.append({
                    'id': f"venta-{venta.id}",
                    'description': f"Nuevo pedido #{venta.id} creado por {user_name}.",
                    'timestamp': venta.fecha.isoformat(),
                    'type': 'order_created',
                    'entity_name': f"Pedido #{venta.id}"
                })

            # Actividades: Nuevos Usuarios
            for new_user in user_qs.order_by('-date_joined')[:3]:
                if not new_user.is_superuser:
                    recent_activities_list.append({
                        'id': f"user-{new_user.id}",
                        'description': f"Nuevo usuario registrado: {new_user.first_name or new_user.email}.",
                        'timestamp': new_user.date_joined.isoformat(),
                        'type': 'user_created',
                        'user_name': new_user.first_name,
                    })

            # Actividades: Productos Bajo Stock (como alerta)
            for prod_name in dashboard_data['productos_bajo_stock'][:3]:
                recent_activities_list.append({
                    'id': f"stock-alert-{prod_name}-{timezone.now().timestamp()}",
                    'description': f"Alerta crítica: Producto '{prod_name}' con stock bajo.",
                    'timestamp': timezone.now().isoformat(),
                    'type': 'alert',
                    'entity_name': prod_name,
                })

            dashboard_data['recent_activities'] = sorted(recent_activities_list, key=lambda x: x['timestamp'],
                                                         reverse=True)[:10]

            serializer = DashboardERPSerializer(dashboard_data)
            return Response(serializer.data)

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error en DashboardERPView: {str(e)}")
            return Response(
                {"error": f"Ha ocurrido un error al obtener las estadísticas del dashboard. Detalles: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )