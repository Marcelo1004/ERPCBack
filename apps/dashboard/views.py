# dashboard/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Count, Sum, F, ExpressionWrapper, DecimalField
from django.db.models.functions import TruncMonth
from rest_framework.permissions import IsAuthenticated, BasePermission
from datetime import datetime, timedelta
from django.utils import timezone

# Importa tus modelos. ¡ASEGÚRATE DE QUE ESTAS RUTAS SEAN CORRECTAS!
from apps.usuarios.models import User
from apps.empresas.models import Empresa
from apps.sucursales.models import Sucursal
from apps.almacenes.models import Almacen
from apps.categorias.models import Categoria
from apps.productos.models import Producto
from apps.suscripciones.models import Suscripcion

# === ¡IMPORTACIONES DE MODELOS DE VENTAS Y DETALLEVENTA! ===
from apps.ventas.models import Venta, DetalleVenta

from .serializers import DashboardERPSerializer


class IsWorkerUser(BasePermission):
    """
    Permiso personalizado para permitir acceso a SuperUsuarios, Administrativos y Empleados.
    Los clientes no tienen acceso al dashboard.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    (request.user.is_superuser or
                     request.user.role in ['ADMINISTRATIVO', 'EMPLEADO']))


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
        }

        try:
            # Determinamos los querysets base que serán filtrados por empresa o serán globales
            if user.is_superuser:
                user_qs = User.objects.all()
                empresa_qs = Empresa.objects.all()
                sucursal_qs = Sucursal.objects.all()
                almacen_qs = Almacen.objects.all()
                categoria_qs = Categoria.objects.all()
                producto_qs = Producto.objects.all()
                venta_qs = Venta.objects.all()
                detalle_venta_qs = DetalleVenta.objects.all()

            elif user.empresa:
                empresa_obj = user.empresa
                user_qs = User.objects.filter(empresa=empresa_obj)
                empresa_qs = Empresa.objects.filter(id=empresa_obj.id)
                sucursal_qs = Sucursal.objects.filter(empresa=empresa_obj)
                almacen_qs = Almacen.objects.filter(empresa=empresa_obj)
                categoria_qs = Categoria.objects.filter(empresa=empresa_obj)
                producto_qs = Producto.objects.filter(empresa=empresa_obj)

                # Asumo que Venta tiene una ForeignKey a Empresa.
                venta_qs = Venta.objects.filter(empresa=empresa_obj)
                # Asumo que DetalleVenta se relaciona con Venta, y Venta con Empresa.
                detalle_venta_qs = DetalleVenta.objects.filter(venta__empresa=empresa_obj)
            else:
                return Response(
                    {"message": "No hay datos de dashboard disponibles para su cuenta o empresa."},
                    status=status.HTTP_200_OK
                )

            # -----------------------------------------------------------
            # CÁLCULO DE MÉTRICAS EXISTENTES Y NUEVAS
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

            if user.is_superuser:
                dashboard_data['total_empresas'] = empresa_qs.count()
                suscripciones_dist = empresa_qs.values(
                    plan_nombre=F('suscripcion__nombre')
                ).annotate(
                    cantidad_empresas=Count('id')
                ).order_by('plan_nombre')
                dashboard_data['distribucion_suscripciones'] = list(suscripciones_dist)
            else:
                dashboard_data['total_empresas'] = 0
                dashboard_data['distribucion_suscripciones'] = []

            # === 1. VENTAS MENSUALES (monthly_sales) ===
            monthly_sales_data = []
            today = timezone.now()
            for i in range(6, -1, -1):  # Desde 6 meses atrás hasta el mes actual
                month_date = (today - timedelta(days=30 * i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                next_month_start = (month_date + timedelta(days=32)).replace(day=1, hour=0, minute=0, second=0,
                                                                             microsecond=0)

                # Filtra las ventas para el rango del mes usando venta_qs (que ya está filtrado por empresa si aplica)
                monthly_sum_agg = venta_qs.filter(
                    fecha__gte=month_date,
                    fecha__lt=next_month_start,
                ).aggregate(total_ventas=Sum('monto_total'))['total_ventas']

                monthly_sales_data.append({
                    'name': month_date.strftime('%b'),
                    'Ventas': float(monthly_sum_agg) if monthly_sum_agg else 0.00
                })
            dashboard_data['monthly_sales'] = monthly_sales_data
            print(f"DEBUG: Monthly Sales Data: {monthly_sales_data}")  # DEBUG PRINT

            # === 2. PRODUCTOS MÁS VENDIDOS (top_products) ===
            top_products_data = []
            # Usa detalle_venta_qs (ya filtrado por empresa si aplica)
            top_products_results = detalle_venta_qs.values(
                'producto__nombre'
            ).annotate(
                # Suma el valor total de la venta de este producto (cantidad * precio_unitario del detalle)
                sales=Sum(F('cantidad') * F('precio_unitario'),
                          output_field=DecimalField(max_digits=15, decimal_places=2)),
                units=Sum('cantidad')  # Suma la cantidad total de unidades vendidas de este producto
            ).order_by('-sales')[:5]  # Top 5 productos por valor de ventas

            for item in top_products_results:
                top_products_data.append({
                    'name': item['producto__nombre'],
                    'sales': float(item['sales'] or 0.00),
                    'units': item['units'] or 0
                })
            dashboard_data['top_products'] = top_products_data
            print(f"DEBUG: Top Products Data: {top_products_data}")  # DEBUG PRINT

            # === 3. DISTRIBUCIÓN POR CATEGORÍA (category_distribution) ===
            category_distribution_data = list(
                producto_qs.values(name=F('categoria__nombre')).annotate(
                    products_count=Count('id')
                ).order_by('name')
            )
            dashboard_data['category_distribution'] = [
                item for item in category_distribution_data if item['name'] is not None
            ]
            print(f"DEBUG: Category Distribution Data: {dashboard_data['category_distribution']}")  # DEBUG PRINT

            # === 4. INVENTARIO POR ALMACÉN (inventory_by_warehouse) ===
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
            print(f"DEBUG: Inventory By Warehouse Data: {dashboard_data['inventory_by_warehouse']}")  # DEBUG PRINT

            # === 5. ACTIVIDADES RECIENTES (recent_activities) ===
            recent_activities_list = []  # Usamos un nombre de variable diferente para evitar cualquier conflicto

            # 5.1 Actividades: Nuevas Ventas/Pedidos
            for venta in venta_qs.order_by('-fecha')[:5]:
                # Aseguramos que usuario no sea None antes de intentar acceder a first_name
                user_name = venta.usuario.first_name if venta.usuario and venta.usuario.first_name else 'Usuario Desconocido'
                recent_activities_list.append({
                    'id': f"venta-{venta.id}",
                    'description': f"Nuevo pedido #{venta.id} creado por {user_name}.",
                    'timestamp': venta.fecha.isoformat(),
                    'type': 'order_created',
                    'entity_name': f"Pedido #{venta.id}"
                })

            # 5.2 Actividades: Nuevos Usuarios
            for new_user in user_qs.order_by('-date_joined')[:3]:
                if not new_user.is_superuser:  # No incluir superusuarios aquí
                    recent_activities_list.append({
                        'id': f"user-{new_user.id}",
                        'description': f"Nuevo usuario registrado: {new_user.first_name or new_user.email}.",
                        'timestamp': new_user.date_joined.isoformat(),
                        'type': 'user_created',
                        'user_name': new_user.first_name,
                    })

            # 5.3 Actividades: Productos Bajo Stock (como alerta)
            for prod_name in dashboard_data['productos_bajo_stock'][:3]:
                recent_activities_list.append({
                    'id': f"stock-alert-{prod_name}-{timezone.now().timestamp()}",
                    'description': f"Alerta crítica: Producto '{prod_name}' con stock bajo.",
                    'timestamp': timezone.now().isoformat(),
                    'type': 'alert',
                    'entity_name': prod_name,
                })

            # Ordenar todas las actividades por fecha descendente y limitar
            dashboard_data['recent_activities'] = sorted(recent_activities_list, key=lambda x: x['timestamp'],
                                                         reverse=True)[:10]
            print(f"DEBUG: Recent Activities Data: {dashboard_data['recent_activities']}")  # DEBUG PRINT

            # Serializar y devolver la respuesta
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