# reports/views.py

from rest_framework import generics, status, serializers
from django.db.models.functions import Coalesce, Concat
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Avg, Count, F, Q,Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from django.http import HttpResponse  # Para exportar archivos
import openpyxl  # Para exportar a Excel
from io import BytesIO  # Para manejar archivos en memoria

# Para PDF
from django.template.loader import get_template
from xhtml2pdf import pisa

from apps.ventas.models import Venta, DetalleVenta
from apps.productos.models import Producto
from apps.usuarios.models import CustomUser
from apps.empresas.models import Empresa
from apps.categorias.models import Categoria
from apps.almacenes.models import Almacen

from .serializers import (
    SalesSummaryReportSerializer,
    TopSellingProductReportSerializer,
    StockLevelReportSerializer,
    ClientPerformanceReportSerializer
)


# Definir una clase base para los métodos de exportación.
# Estos métodos serán llamados directamente desde urls.py y deben manejar el objeto HttpRequest.
class ReportExportMixin:
    @classmethod
    def _get_params(cls, request):
        """
        Método auxiliar para obtener parámetros de consulta,
        adaptándose si request.query_params (DRF) o request.GET (Django puro) está disponible.
        """
        # Si la solicitud proviene de una vista DRF (as_view()), tendrá query_params
        if hasattr(request, 'query_params'):
            return request.query_params
        # Si es una solicitud directa de Django (ej. para un método de exportación), usará GET
        return request.GET

    @classmethod
    def _create_instance_and_get_data(cls, request):
        """
        Crea una instancia de la vista y llama a _get_report_data.
        Ajusta la request para que la instancia pueda acceder a los parámetros.
        """
        instance = cls()
        instance.request = request  # Asignar la request al atributo de la instancia
        # Necesario para que los métodos como get_company_filter y get_date_range_filter
        # puedan acceder a la request.

        # Si la vista original hereda de GenericAPIView, necesita setup().
        # Si solo es un @classmethod, no tiene un request.resolver_match.args, etc.
        # Por eso, la forma más robusta para estos classmethods que llaman a métodos de instancia
        # que a su vez acceden a `self.request` es pasarles la request explícitamente o
        # adaptar los métodos de filtrado para que la reciban.
        # Ya que get_company_filter y get_date_range_filter acceden a `self.request`,
        # debemos inicializar `instance.request`.

        # Los métodos de filtro (get_company_filter, get_date_range_filter) ahora
        # usan _get_params(self.request), lo que los hace compatibles.
        return instance._get_report_data(request), instance.get_company_filter(request)

    @classmethod
    def export_excel(cls, request, *args, **kwargs):
        report_data, company_filter = cls._create_instance_and_get_data(request)

        # Ajustar headers y data según el tipo de reporte
        if cls == SalesSummaryReportView:
            headers = ["Total Ventas", "Monto Total Ventas", "Promedio por Venta"]
            data_to_excel = [
                report_data]  # Resumen es un único dict, se envuelve en lista para _generate_excel_response
        elif cls == TopSellingProductsReportView:
            headers = ["ID Producto", "Nombre Producto", "Cantidad Vendida", "Ingresos Generados"]
            data_to_excel = [{
                "ID Producto": p['id'],  # Usamos 'id' aquí
                "Nombre Producto": p['nombre'],
                "Cantidad Vendida": p['cantidad_vendida'],
                "Ingresos Generados": float(p['ingresos_generados'])  # Convertir a float
            } for p in report_data]
        elif cls == StockLevelReportView:
            headers = ["ID Producto", "Nombre Producto", "Stock Actual", "Nombre Almacén", "Nombre Empresa"]
            data_to_excel = report_data  # Ya está en formato de lista de dicts
        elif cls == ClientPerformanceReportView:
            headers = ["ID Cliente", "Nombre Cliente", "Email Cliente", "Monto Total Comprado", "Número Ventas"]
            data_to_excel = report_data  # Ya está en formato de lista de dicts
        else:
            return HttpResponse("Tipo de reporte no reconocido para exportación Excel",
                                status=status.HTTP_400_BAD_REQUEST)

        instance = cls()
        return instance._generate_excel_response(data_to_excel, headers,
                                                 sheet_name=cls.__name__.replace('View', '').replace('Report', ''))

    @classmethod
    def export_pdf(cls, request, *args, **kwargs):
        report_data, company_filter = cls._create_instance_and_get_data(request)

        company_name = "Todas las Empresas"
        if company_filter and 'empresa_id' in company_filter and company_filter['empresa_id'] is not None:
            try:
                company = Empresa.objects.get(id=int(company_filter['empresa_id']))
                company_name = company.nombre
            except (ValueError, Empresa.DoesNotExist):
                pass

        context = {
            'generated_date': timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
            'company_name': company_name,
            'report_data': report_data,  # Pasa la data tal cual como la devuelve _get_report_data
        }

        template_map = {
            SalesSummaryReportView: 'reports/sales_summary_report.html',
            TopSellingProductsReportView: 'reports/top_selling_products_report.html',
            StockLevelReportView: 'reports/stock_level_report.html',
            ClientPerformanceReportView: 'reports/client_performance_report.html',
        }
        title_map = {
            SalesSummaryReportView: 'Reporte de Resumen de Ventas',
            TopSellingProductsReportView: 'Reporte de Productos Más Vendidos',
            StockLevelReportView: 'Reporte de Nivel de Stock',
            ClientPerformanceReportView: 'Reporte de Rendimiento de Clientes',
        }

        template_name = template_map.get(cls)
        context['title'] = title_map.get(cls, "Reporte")

        if not template_name:
            return HttpResponse("Tipo de reporte no reconocido para exportación PDF",
                                status=status.HTTP_400_BAD_REQUEST)

        instance = cls()
        return instance._generate_pdf_response(template_name, context,
                                               file_name=cls.__name__.replace('View', '').replace('Report', ''))

    @classmethod
    def export_txt(cls, request, *args, **kwargs):
        report_data, company_filter = cls._create_instance_and_get_data(request)

        company_name = "Todas las Empresas"
        if company_filter and 'empresa_id' in company_filter and company_filter['empresa_id'] is not None:
            try:
                company = Empresa.objects.get(id=int(company_filter['empresa_id']))
                company_name = company.nombre
            except (ValueError, Empresa.DoesNotExist):
                pass

        content_map = {
            SalesSummaryReportView: lambda data, c_name: f"""REPORTE DE RESUMEN DE VENTAS
Fecha de Generación: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}
Empresa: {c_name}

Total Ventas: {data['total_ventas_cantidad']}
Monto Total Ventas: {data['monto_total_ventas']}
Promedio por Venta: {data['promedio_por_venta']}
""",
            TopSellingProductsReportView: lambda data, c_name: f"""REPORTE DE PRODUCTOS MÁS VENDIDOS
Fecha de Generación: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}
Empresa: {c_name}

ID Producto | Nombre Producto           | Cantidad Vendida | Ingresos Generados
---------------------------------------------------------------------------------
""" + "".join([f"{p['id']:<11} | {p['nombre'][:25]:<25} | {p['cantidad_vendida']:<16} | {p['ingresos_generados']}\n" for
               p in data]),

            StockLevelReportView: lambda data, c_name: f"""REPORTE DE NIVEL DE STOCK
Fecha de Generación: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}
Empresa: {c_name}

ID Producto | Nombre Producto           | Stock Actual | Nombre Almacén          | Nombre Empresa
-----------------------------------------------------------------------------------------------------
""" + "".join([
                                                                                                                                                                 f"{item['id']:<11} | {item['nombre'][:25]:<25} | {item['stock_actual']:<12} | {item['almacen_nombre'][:25]:<25} | {item['empresa_nombre'][:25]:<25}\n"
                                                                                                                                                                 for
                                                                                                                                                                 item
                                                                                                                                                                 in
                                                                                                                                                                 data]),

            ClientPerformanceReportView: lambda data, c_name: f"""REPORTE DE RENDIMIENTO DE CLIENTES
Fecha de Generación: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}
Empresa: {c_name}

ID Cliente | Nombre Cliente            | Email Cliente             | Monto Total Comprado | Número Ventas
-----------------------------------------------------------------------------------------------------------------
""" + "".join([
                                                                                                                                                                        f"{client['id']:<10} | {client['nombre_cliente'][:25]:<25} | {client['email_cliente'][:25]:<25} | {client['monto_total_comprado']:<20} | {client['numero_ventas_realizadas']}\n"
                                                                                                                                                                        for
                                                                                                                                                                        client
                                                                                                                                                                        in
                                                                                                                                                                        data]),
        }

        content = content_map.get(cls)
        if callable(content):  # Para los reportes que usan lambda (lista de datos)
            content_str = content(report_data, company_name)
        else:  # Para el resumen de ventas (objeto único)
            content_str = content

        if not content_str:
            return HttpResponse("Tipo de reporte no reconocido para exportación TXT",
                                status=status.HTTP_400_BAD_REQUEST)

        instance = cls()
        return instance._generate_txt_response(content_str,
                                               file_name=cls.__name__.replace('View', '').replace('Report', ''))


class BaseReportView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    # --- CAMBIO AQUÍ: Ahora get_company_filter recibe `request` directamente ---
    def get_company_filter(self, request):
        params = ReportExportMixin._get_params(request)  # Usa el método auxiliar
        empresa_id = params.get('empresa_id')

        if not request.user.is_superuser:
            if request.user.empresa_detail:
                return {'empresa_id': request.user.empresa_detail.id}
            else:
                raise serializers.ValidationError({"detail": "El usuario no está asociado a ninguna empresa."})

        if empresa_id:
            try:
                empresa_id = int(empresa_id)
                if not Empresa.objects.filter(id=empresa_id).exists():
                    raise serializers.ValidationError({"empresa_id": "La empresa especificada no existe."})
                return {'empresa_id': empresa_id}
            except ValueError:
                raise serializers.ValidationError({"empresa_id": "El ID de empresa debe ser un número válido."})
        else:
            return {}

            # --- CAMBIO AQUÍ: Ahora get_date_range_filter recibe `request` directamente ---

    def get_date_range_filter(self, request, date_field='fecha'):
        params = ReportExportMixin._get_params(request)  # Usa el método auxiliar
        fecha_inicio_str = params.get('fecha_inicio')
        fecha_fin_str = params.get('fecha_fin')

        date_filter = {}
        if fecha_inicio_str:
            try:
                date_filter[f'{date_field}__gte'] = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
            except ValueError:
                raise serializers.ValidationError({"fecha_inicio": "Formato de fecha inválido. Use %Y-%m-%d."})
        if fecha_fin_str:
            try:
                fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
                date_filter[f'{date_field}__lt'] = fecha_fin + timedelta(days=1)
            except ValueError:
                raise serializers.ValidationError({"fecha_fin": "Formato de fecha inválido. Use %Y-%m-%d."})

        if not date_filter:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=90)
            date_filter[f'{date_field}__gte'] = start_date
            date_filter[f'{date_field}__lt'] = end_date + timedelta(days=1)

        return date_filter

    def _generate_excel_response(self, data, headers, sheet_name="Reporte"):
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = sheet_name

        sheet.append(headers)

        for row_data in data:
            row = []
            for header_label in headers:
                header_key_map = {
                    "Total Ventas": "total_ventas_cantidad",
                    "Monto Total Ventas": "monto_total_ventas",
                    "Promedio por Venta": "promedio_por_venta",
                    "ID Producto": "id",
                    "Nombre Producto": "nombre",
                    "Cantidad Vendida": "cantidad_vendida",
                    "Ingresos Generados": "ingresos_generados",
                    "Stock Actual": "stock_actual",
                    "Nombre Almacén": "almacen_nombre",
                    "Nombre Empresa": "empresa_nombre",
                    "ID Cliente": "id",
                    "Nombre Cliente": "nombre_cliente",
                    "Email Cliente": "email_cliente",
                    "Monto Total Comprado": "monto_total_comprado",
                    "Número Ventas": "numero_ventas_realizadas",
                }
                key_to_access = header_key_map.get(header_label, header_label)
                value = row_data.get(key_to_access)  # Accede al valor por la clave mapeada

                if isinstance(value, Decimal):
                    row.append(float(value))
                else:
                    row.append(value)
            sheet.append(row)

        buffer = BytesIO()
        workbook.save(buffer)
        buffer.seek(0)

        response = HttpResponse(buffer.getvalue(),
                                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response[
            'Content-Disposition'] = f'attachment; filename="{sheet_name}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        return response



    def _generate_pdf_response(self, template_name, context, file_name="reporte.pdf"):
        template = get_template(template_name)
        # --- CAMBIO AQUÍ: Elimina 'Context()' ---
        html = template.render(context)
        result = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
        if not pdf.err:
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            response[
                'Content-Disposition'] = f'attachment; filename="{file_name}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
            return response
        return HttpResponse('Error al generar PDF', status=status.HTTP_500_INTERNAL_SERVER_ERROR)



    def _generate_txt_response(self, content, file_name="reporte.txt"):
        response = HttpResponse(content, content_type='text/plain')
        response[
            'Content-Disposition'] = f'attachment; filename="{file_name}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.txt"'
        return response


class SalesSummaryReportView(BaseReportView, ReportExportMixin):
    def _get_report_data(self, request):
        company_filter = self.get_company_filter(request)  # Pasa la request
        date_filter = self.get_date_range_filter(request, date_field='fecha')  # Pasa la request
        params = ReportExportMixin._get_params(request)  # Usa el método auxiliar
        cliente_id = params.get('cliente_id')
        estado = params.get('estado')

        filters = {**company_filter, **date_filter}
        if cliente_id:
            try:
                filters['usuario_id'] = int(cliente_id)
                if not CustomUser.objects.filter(id=filters['usuario_id']).exists():
                    raise serializers.ValidationError({"cliente_id": "El cliente especificado no existe."})
            except ValueError:
                raise serializers.ValidationError({"cliente_id": "El ID de cliente debe ser un número válido."})
        if estado:
            if estado not in ['Pendiente', 'Completada', 'Cancelada']:
                raise serializers.ValidationError({"estado": "Estado de venta inválido."})
            filters['estado'] = estado

        ventas_qs = Venta.objects.filter(**filters)

        total_ventas_cantidad = ventas_qs.count()
        monto_total_ventas = ventas_qs.aggregate(
            total=Coalesce(Sum('monto_total'), Decimal('0.00'))
        )['total']

        promedio_por_venta = Decimal('0.00')
        if total_ventas_cantidad > 0:
            promedio_por_venta = (monto_total_ventas / total_ventas_cantidad).quantize(Decimal('0.01'))

        return {
            'total_ventas_cantidad': total_ventas_cantidad,
            'monto_total_ventas': monto_total_ventas,
            'promedio_por_venta': promedio_por_venta,
        }

    def get(self, request, *args, **kwargs):
        report_data = self._get_report_data(request)
        serializer = SalesSummaryReportSerializer(report_data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TopSellingProductsReportView(BaseReportView, ReportExportMixin):
    def _get_report_data(self, request):
        company_filter = self.get_company_filter(request)  # Pasa la request
        date_filter = self.get_date_range_filter(request, date_field='fecha')  # Pasa la request
        params = ReportExportMixin._get_params(request)  # Usa el método auxiliar
        categoria_id = params.get('categoria_id')
        limit = params.get('limit', 10)

        filters = {**company_filter, **date_filter}
        if categoria_id:
            try:
                filters['detalles__producto__categoria_id'] = int(categoria_id)
                if not Categoria.objects.filter(id=filters['detalles__producto__categoria_id']).exists():
                    raise serializers.ValidationError({"categoria_id": "La categoría especificada no existe."})
            except ValueError:
                raise serializers.ValidationError({"categoria_id": "El ID de categoría debe ser un número válido."})

        try:
            limit = int(limit)
            if limit <= 0: raise ValueError
        except ValueError:
            raise serializers.ValidationError({"limit": "El límite debe ser un número entero positivo."})

        ventas_filtradas_ids = Venta.objects.filter(**filters).values_list('id', flat=True)

        top_products = DetalleVenta.objects.filter(venta_id__in=ventas_filtradas_ids) \
                           .values(
            'producto__id',  # <--- Aquí debe ser 'producto__id'
            'producto__nombre',  # <--- Aquí debe ser 'producto__nombre'
            'cantidad',
            'precio_unitario',
            'descuento_aplicado'
        ) \
                           .annotate(
            # Asegúrate de que los nombres de los campos anotados coincidan con el serializer
            id=F('producto__id'),  # <--- Renombrar a 'id'
            nombre=F('producto__nombre'),  # <--- Renombrar a 'nombre'
            cantidad_vendida=Sum('cantidad'),
            ingresos_generados=Coalesce(
                Sum(F('cantidad') * F('precio_unitario') * (Decimal('1.00') - F('descuento_aplicado'))),
                Decimal('0.00')
            )
        ) \
                           .order_by('-cantidad_vendida')[:limit]

        # Eliminar las claves originales si solo queremos las renombradas para el serializer
        # Esto es importante para que el serializer no encuentre 'producto__id'/'producto__nombre' si solo espera 'id'/'nombre'
        final_data = []
        for item in top_products:
            # Crea un nuevo diccionario con las claves que espera el serializer
            final_data.append({
                'id': item['id'],
                'nombre': item['nombre'],
                'cantidad_vendida': item['cantidad_vendida'],
                'ingresos_generados': item['ingresos_generados']
            })
        return final_data

    def get(self, request, *args, **kwargs):
        report_data = self._get_report_data(request)
        serialized_data = TopSellingProductReportSerializer(report_data, many=True).data
        return Response(serialized_data, status=status.HTTP_200_OK)


class StockLevelReportView(BaseReportView, ReportExportMixin):
    def _get_report_data(self, request):
        company_filter = self.get_company_filter(request)  # Pasa la request
        almacen_id = ReportExportMixin._get_params(request).get('almacen_id')
        categoria_id = ReportExportMixin._get_params(request).get('categoria_id')
        stock_min = ReportExportMixin._get_params(request).get('stock_min')
        stock_max = ReportExportMixin._get_params(request).get('stock_max')

        filters = {**company_filter}
        if almacen_id:
            try:
                filters['almacen_id'] = int(almacen_id)
                if not Almacen.objects.filter(id=filters['almacen_id']).exists():
                    raise serializers.ValidationError({"almacen_id": "El almacén especificado no existe."})
            except ValueError:
                raise serializers.ValidationError({"almacen_id": "El ID de almacén debe ser un número válido."})
        if categoria_id:
            try:
                filters['categoria_id'] = int(categoria_id)
                if not Categoria.objects.filter(id=filters['categoria_id']).exists():
                    raise serializers.ValidationError({"categoria_id": "La categoría especificada no existe."})
            except ValueError:
                raise serializers.ValidationError({"categoria_id": "El ID de categoría debe ser un número válido."})

        if stock_min:
            try:
                filters['stock__gte'] = int(stock_min)
                if filters['stock__gte'] < 0: raise ValueError
            except ValueError:
                raise serializers.ValidationError(
                    {"stock_min": "El stock mínimo debe ser un número entero no negativo."})
        if stock_max:
            try:
                filters['stock__lte'] = int(stock_max)
                if filters['stock__lte'] < 0: raise ValueError
            except ValueError:
                raise serializers.ValidationError(
                    {"stock_max": "El stock máximo debe ser un número entero no negativo."})

        productos_qs = Producto.objects.filter(**filters) \
            .select_related('almacen', 'empresa', 'categoria') \
            .values('id', 'nombre', 'stock', 'almacen__nombre', 'empresa__nombre') \
            .order_by('nombre')

        report_data = []
        for p in productos_qs:
            report_data.append({
                'id': p['id'],
                'nombre': p['nombre'],
                'stock_actual': p['stock'],
                'almacen_nombre': p['almacen__nombre'] if p['almacen__nombre'] else 'N/A',
                'empresa_nombre': p['empresa__nombre'] if p['empresa__nombre'] else 'N/A',
            })
        return report_data

    def get(self, request, *args, **kwargs):
        report_data = self._get_report_data(request)
        serializer = StockLevelReportSerializer(report_data, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ClientPerformanceReportView(BaseReportView, ReportExportMixin):
    def _get_report_data(self, request):
        company_filter = self.get_company_filter(request)  # Pasa la request
        date_filter = self.get_date_range_filter(request, date_field='fecha')  # Pasa la request

        filters = {**company_filter, **date_filter}

        client_performance = Venta.objects.filter(**filters) \
            .values('usuario__id', 'usuario__first_name', 'usuario__last_name', 'usuario__email') \
            .annotate(
            # Asegúrate de que los nombres de los campos anotados coincidan con el serializer
            id=F('usuario__id'),  # Renombrar a 'id'
            nombre_cliente=Concat(
                Coalesce(F('usuario__first_name'), Value('')),  # Coalesce a cadena vacía
                Value(' '),  # Espacio como Value
                Coalesce(F('usuario__last_name'), Value(''))  # Coalesce a cadena vacía
            ),
            email_cliente=F('usuario__email'),
            monto_total_comprado=Coalesce(Sum('monto_total'), Decimal('0.00')),
            numero_ventas_realizadas=Count('id')
        ) \
            .order_by('-monto_total_comprado')

        final_data = []
        for client in client_performance:
            final_data.append({
                'id': client['id'],
                'nombre_cliente': client['nombre_cliente'].strip(),
                'email_cliente': client['email_cliente'],
                'monto_total_comprado': client['monto_total_comprado'],
                'numero_ventas_realizadas': client['numero_ventas_realizadas'],
            })
        return final_data

    def get(self, request, *args, **kwargs):
        report_data = self._get_report_data(request)
        serializer = ClientPerformanceReportSerializer(report_data, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)