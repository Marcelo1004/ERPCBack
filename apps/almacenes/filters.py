import django_filters
from .models import Almacen

class AlmacenFilter(django_filters.FilterSet):
    """
    Filtros para el modelo Almacen.
    Permite filtrar por el ID de la sucursal a la que pertenece el almacén.
    """
    # Filtro para el campo 'sucursal' (por ID numérico)
    sucursal = django_filters.NumberFilter(field_name='sucursal')
    # Opcional: Si también quieres buscar por nombre de almacén
    nombre = django_filters.CharFilter(field_name='nombre', lookup_expr='icontains')


    class Meta:
        model = Almacen
        fields = ['sucursal', 'nombre'] # Los campos que se pueden filtrar