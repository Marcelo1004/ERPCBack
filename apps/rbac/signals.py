# apps/rbac/signals.py

from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.apps import apps  # Para acceder a los modelos dinámicamente


@receiver(post_migrate)
def create_default_roles_and_permissions(sender, **kwargs):
    """
    Crea roles y permisos por defecto después de que las migraciones se hayan aplicado.
    Solo se ejecuta para la app 'rbac' para evitar duplicados o ejecuciones innecesarias.
    """
    # Asegúrate de que esto solo se ejecute para la app 'rbac'
    # y solo cuando se están ejecutando las migraciones para una aplicación específica
    if kwargs.get('app_config') is None or kwargs.get('app_config').name != 'apps.rbac':
        return

    # Usar apps.get_model para evitar importaciones circulares y asegurar que los modelos estén listos
    Role = apps.get_model('rbac', 'Role')
    Permission = apps.get_model('rbac', 'Permission')
    User = apps.get_model('usuarios', 'CustomUser')  # Asume que tu modelo de usuario es CustomUser en la app 'users'

    print("Iniciando seeder de roles y permisos por defecto...")

    # --- Crear Permisos por Defecto ---
    permissions_data = [
        {'name': 'Acceso al Panel de Administración', 'code_name': 'access_admin_panel',
         'description': 'Permite el acceso a las secciones de administración.'},
        {'name': 'Gestionar Usuarios', 'code_name': 'manage_users',
         'description': 'Permite crear, ver, editar y eliminar usuarios.'},
        {'name': 'Gestionar Empresas', 'code_name': 'manage_empresas',
         'description': 'Permite crear, ver, editar y eliminar empresas.'},
        {'name': 'Gestionar Productos', 'code_name': 'manage_products',
         'description': 'Permite crear, ver, editar y eliminar productos.'},
        {'name': 'Gestionar Ventas', 'code_name': 'manage_sales',
         'description': 'Permite crear, ver, editar y eliminar ventas.'},
        {'name': 'Gestionar Proveedores', 'code_name': 'manage_proveedores',
         'description': 'Permite crear, ver, editar y eliminar proveedores.'},
        {'name': 'Ver Reportes', 'code_name': 'view_reports',
         'description': 'Permite ver los reportes y estadísticas del sistema.'},
        {'name': 'Asignar Roles a Usuarios', 'code_name': 'assign_roles_to_users',
         'description': 'Permite al superusuario asignar roles a otros usuarios.'},
    ]

    for p_data in permissions_data:
        # get_or_create previene duplicados
        permission, created = Permission.objects.get_or_create(code_name=p_data['code_name'], defaults=p_data)
        if created:
            print(f"Permiso '{permission.name}' creado.")

    # Recargar los permisos para asegurarnos de tener las instancias actualizadas
    # Convertir a diccionario para un acceso rápido por code_name
    all_permissions = {p.code_name: p for p in Permission.objects.all()}

    # --- Crear Roles por Defecto y Asignar Permisos ---
    roles_data = [
        {
            'name': 'Super Usuario',
            'description': 'Rol con acceso total al sistema. Exclusivo para el superusuario.',
            'assigned_permissions_codes': list(all_permissions.keys())  # Asigna todos los permisos creados
        },
        {
            'name': 'Administrador',
            'description': 'Rol para la administración de una empresa, con gestión de usuarios, productos, ventas, proveedores y acceso a reportes.',
            'assigned_permissions_codes': [
                'access_admin_panel', 'manage_users', 'manage_products',
                'manage_sales', 'manage_proveedores', 'view_reports',
            ]
        },
        {
            'name': 'Empleado',
            'description': 'Rol para empleados con acceso a funcionalidades básicas como gestión de productos, ventas y proveedores.',
            'assigned_permissions_codes': [
                'manage_products', 'manage_sales', 'manage_proveedores',
            ]
        },
        {
            'name': 'Cliente',
            'description': 'Rol por defecto para usuarios clientes.',
            'assigned_permissions_codes': []  # Sin permisos por defecto
        },
    ]

    for r_data in roles_data:
        # Obtener las instancias de permisos basadas en los code_names
        assigned_permissions_instances = [
            all_permissions[code] for code in r_data['assigned_permissions_codes'] if code in all_permissions
        ]

        role, created = Role.objects.get_or_create(name=r_data['name'],
                                                   defaults={'description': r_data['description'], 'is_active': True})

        if created:
            role.permissions.set(assigned_permissions_instances)
            print(f"Rol '{role.name}' creado y permisos asignados.")
        else:
            # Si el rol ya existe, se actualizan sus permisos para asegurar consistencia
            current_permission_ids = set(role.permissions.values_list('id', flat=True))
            new_permission_ids = set([p.id for p in assigned_permissions_instances])
            if current_permission_ids != new_permission_ids:
                role.permissions.set(assigned_permissions_instances)
                print(f"Permisos del rol '{role.name}' actualizados.")

    # --- Asignar el rol 'Super Usuario' al superusuario existente (si lo hay) ---
    try:
        superuser_role_obj = Role.objects.get(name='Super Usuario')
        # Filtra por usuarios que son superusuarios pero que aún no tienen un rol asignado
        for user_instance in User.objects.filter(is_superuser=True, role__isnull=True):
            user_instance.role = superuser_role_obj
            user_instance.save()
            print(f"Rol 'Super Usuario' asignado a '{user_instance.username}'.")
    except Role.DoesNotExist:
        print(
            "Advertencia: El rol 'Super Usuario' no existe. No se pudo asignar a superusuarios existentes automáticamente.")
    except Exception as e:
        print(f"Error al asignar rol de superusuario en post_migrate: {e}")

    print("Seeder de roles y permisos completado.")