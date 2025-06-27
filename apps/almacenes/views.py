# apps/almacenes/views.py

from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError

# Importa tus serializers y modelos
from .serializers import AlmacenSerializer
from .models import Almacen

# Importa tus permisos centralizados
from erp.permissions import IsAdminOrSuperUser, IsEmployeeOrHigher


class AlmacenViewSet(viewsets.ModelViewSet):
    queryset = Almacen.objects.all()
    serializer_class = AlmacenSerializer
    permission_classes = [IsAdminOrSuperUser | IsEmployeeOrHigher]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Almacen.objects.none()

        user = self.request.user
        queryset = super().get_queryset()

        if user.is_superuser:
            return queryset.order_by('nombre')
        elif user.is_authenticated and hasattr(user, 'role') and user.role and user.role.name in ['Administrador',
                                                                                                  'Empleado']:
            if hasattr(user, 'empresa') and user.empresa:
                return queryset.filter(empresa=user.empresa).order_by('nombre')
            return Almacen.objects.none()
        else:
            return Almacen.objects.none()

    def perform_create(self, serializer):
        user = self.request.user

        print(f"Usuario creando almacén: {user.username}, Superuser: {user.is_superuser}")
        print(f"Datos validados del serializer antes de guardar: {serializer.validated_data}")

        if not user.is_superuser:
            # Para no-superusuarios, la empresa se asigna automáticamente.
            if hasattr(user, 'empresa') and user.empresa:
                # Si el frontend envió un campo 'empresa', validamos que sea la del usuario.
                # Si intentan enviar una empresa diferente, o simplemente enviaron una,
                # nos aseguramos de que sea la del usuario actual.
                if 'empresa' in serializer.validated_data:
                    # Si se envía una empresa, y no es la del usuario, denegar.
                    if serializer.validated_data['empresa'].id != user.empresa.id:
                        raise PermissionDenied("No tienes permiso para crear almacenes en otra empresa.")

                # ¡La clave! Asegurarse de que 'empresa' esté en validated_data para que serializer.save() funcione.
                # Si ya estaba y era la correcta, se mantiene. Si no estaba, se añade.
                # Si estaba y era incorrecta, la línea de arriba ya lanzó una excepción.
                serializer.validated_data['empresa'] = user.empresa  # <--- ¡CAMBIO CRUCIAL AQUÍ!

                serializer.save()
                print(f"Almacén creado para la empresa del usuario: {user.empresa.nombre}")
            else:
                raise PermissionDenied("Tu cuenta no está asociada a una empresa para crear almacenes.")
        else:
            # Si es superusuario, debe especificar la empresa.
            if 'empresa' not in serializer.validated_data or serializer.validated_data['empresa'] is None:
                raise ValidationError({"empresa": "El campo 'empresa' es requerido para superusuarios."})

            # La empresa ya viene en validated_data, simplemente guardamos
            serializer.save()
            print(f"Almacén creado por superusuario para la empresa: {serializer.validated_data['empresa'].nombre}")

    def perform_update(self, serializer):
        user = self.request.user
        instance = self.get_object()

        if not user.is_superuser:
            if hasattr(user, 'empresa') and user.empresa:
                if instance.empresa != user.empresa:
                    raise PermissionDenied("No tienes permiso para actualizar almacenes de otra empresa.")

                # Si intenta cambiar la empresa del almacén (que no debería poder hacer)
                if 'empresa' in serializer.validated_data and serializer.validated_data['empresa'] != user.empresa:
                    raise PermissionDenied("No puedes cambiar la empresa de un almacén.")

                serializer.save()
            else:
                raise PermissionDenied("Tu cuenta no está asociada a una empresa para actualizar almacenes.")
        else:
            serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user

        if not user.is_superuser:
            if hasattr(user, 'empresa') and user.empresa:
                if instance.empresa != user.empresa:
                    raise PermissionDenied("No tienes permiso para eliminar almacenes de otra empresa.")
            else:
                raise PermissionDenied("Tu cuenta no está asociada a una empresa para eliminar almacenes.")

        instance.delete()