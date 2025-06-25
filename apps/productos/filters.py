import django_filters
from .models import Producto

class ProductoFilter(django_filters.FilterSet):
    """
    Filtros para el modelo Producto.
    Permite filtrar por nombre (búsqueda parcial insensible a mayúsculas/minúsculas)
    y por categoría (ID exacto).
    """
    nombre = django_filters.CharFilter(field_name='nombre', lookup_expr='icontains')
    categoria = django_filters.NumberFilter(field_name='categoria')
    # Puedes añadir más filtros aquí si los necesitas, por ejemplo:
    # stock_min = django_filters.NumberFilter(field_name='stock', lookup_expr='gte')
    # precio_max = django_filters.NumberFilter(field_name='precio', lookup_expr='lte')


    class Meta:
        model = Producto
        fields = ['nombre', 'categoria'] # Los campos que se pueden filtrar
        # Si tienes un campo 'search' que no se mapea directamente a un campo del modelo
        # pero quieres usarlo para una búsqueda general en múltiples campos,
        # lo mejor es combinar esto con SearchFilter en la vista.
        # Aquí 'nombre' se mapea al parámetro 'nombre', pero podemos usar 'search' en la URL
        # y mapearlo a 'nombre' en el frontend, y para la categoría 'categoria'.
        # La combinación con SearchFilter en views.py es más potente para 'search'.