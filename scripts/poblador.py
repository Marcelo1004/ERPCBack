# Backend/BackendAISi2-master/backend/scripts/poblador.py

"""
Script para poblar la base de datos con datos de prueba realistas.
"""

import os
import sys
import django
import random
from datetime import datetime, timedelta
from decimal import Decimal

# Asegúrate de tener 'python-dotenv' instalado: pip install python-dotenv
from dotenv import load_dotenv
from django.db import transaction


# --- Configuración del entorno de Django ---

# 1. Cargar variables de entorno desde .env si existe.
#    El .env está en el directorio 'backend', que está un nivel por encima de 'scripts'.
#    Ruta del script: BackendAISi2-master/backend/scripts/poblador.py
#    Ruta del .env:   BackendAISi2-master/backend/.env
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    print("Advertencia: El archivo .env no fue encontrado en la ruta esperada.")

# 2. Añadir la ruta de la raíz del proyecto al sys.path para que Django pueda encontrar las aplicaciones.
#    La raíz del proyecto (donde está manage.py y erp.settings) está un nivel por encima.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

# 3. Establecer la variable de entorno para las configuraciones de Django.
#    'erp' debe ser el nombre del directorio que contiene settings.py (tu proyecto principal de Django).
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erp.settings')

# 4. Inicializar Django. Esto permite que el ORM de Django funcione.
django.setup()

# --- Fin de la configuración del entorno de Django ---


# Importa tus modelos DESPUÉS de django.setup().
# Las rutas ya deberían ser correctas gracias a sys.path.append(project_root)
from apps.usuarios.models import User
from apps.cursos.models import Curso
from apps.materias.models import Materia
from apps.notas.models import Periodo, Nota
from apps.asistencias.models import Asistencia
from apps.participaciones.models import Participacion


print("Iniciando poblamiento de datos...")


def crear_periodos():
    print("Creando periodos academicos...")
    periodos = []

    periodo1, _ = Periodo.objects.get_or_create(
        nombre="Primer Trimestre",
        trimestre="PRIMERO",
        año_academico="2024-2025",
        fecha_inicio=datetime(2024, 8, 1),
        fecha_fin=datetime(2024, 11, 15)
    )
    periodos.append(periodo1)

    periodo2, _ = Periodo.objects.get_or_create(
        nombre="Segundo Trimestre",
        trimestre="SEGUNDO",
        año_academico="2024-2025",
        fecha_inicio=datetime(2024, 11, 16),
        fecha_fin=datetime(2025, 2, 28)
    )
    periodos.append(periodo2)

    periodo3, _ = Periodo.objects.get_or_create(
        nombre="Tercer Trimestre",
        trimestre="TERCERO",
        año_academico="2024-2025",
        fecha_inicio=datetime(2025, 3, 1),
        fecha_fin=datetime(2025, 6, 15)
    )
    periodos.append(periodo3)

    print(f"Periodos creados: {len(periodos)}")
    return periodos


def generar_fechas_clase():
    fecha_inicio = datetime(2024, 8, 1)
    fecha_fin = datetime(2025, 6, 15)

    fechas = []
    fecha_actual = fecha_inicio

    while fecha_actual <= fecha_fin:
        if fecha_actual.weekday() < 5:  # Lunes a Viernes
            fechas.append(fecha_actual.date())
        fecha_actual += timedelta(days=1)

    print(f"Fechas de clase generadas: {len(fechas)}")
    return fechas


def crear_asistencias(cursos, fechas):
    print("Creando asistencias...")
    contador = 0

    for curso in cursos:
        estudiantes = User.objects.filter(curso=curso, role='ESTUDIANTE')
        materias = curso.materias.all()

        # Muestrear algunas fechas para no crear asistencias para cada día
        fechas_muestra = random.sample(fechas, min(len(fechas), 30))

        for fecha in fechas_muestra:
            for estudiante in estudiantes:
                for materia in materias:
                    presente = random.random() <= 0.9  # 90% de probabilidad de presente
                    justificacion = None
                    if not presente:
                        justificacion = random.choice(["Enfermedad", "Cita medica", "Problemas personales"])

                    try:
                        Asistencia.objects.get_or_create(
                            estudiante=estudiante,
                            materia=materia,
                            fecha=fecha,
                            defaults={
                                'presente': presente,
                                'justificacion': justificacion
                            }
                        )
                        contador += 1
                        if contador % 500 == 0:
                            print(f"  {contador} asistencias creadas...")
                    except Exception as e:
                        print(f"Error al crear asistencia: {e}")

    print(f"Total asistencias: {contador}")


def crear_participaciones(cursos, fechas):
    print("Creando participaciones...")
    contador = 0
    tipos = ['VOLUNTARIA', 'SOLICITADA', 'EJERCICIO', 'PRESENTACION', 'DEBATE']

    for curso in cursos:
        estudiantes = User.objects.filter(curso=curso, role='ESTUDIANTE')
        materias = curso.materias.all()

        fechas_muestra = random.sample(fechas, min(len(fechas), 20)) # Muestrear menos fechas para participaciones

        for fecha in fechas_muestra:
            for materia in materias:
                # Seleccionar un subconjunto de estudiantes para participar en cada materia/fecha
                participantes = random.sample(list(estudiantes), min(7, len(estudiantes)))

                for estudiante in participantes:
                    # Cada estudiante puede tener 1 o 2 participaciones por fecha/materia
                    for _ in range(random.randint(1, 2)):
                        tipo = random.choice(tipos)
                        valor = random.randint(6, 10)  # Valores entre 6-10
                        descripcion = f"Participacion {tipo.lower()} en {materia.nombre} el {fecha}"

                        try:
                            Participacion.objects.create(
                                estudiante=estudiante,
                                materia=materia,
                                fecha=fecha,
                                tipo=tipo,
                                valor=valor,
                                descripcion=descripcion
                            )
                            contador += 1
                        except Exception as e:
                            print(f"Error al crear participacion: {e}")

    print(f"Total participaciones: {contador}")


def crear_notas(periodos, cursos):
    print("Creando notas...")
    contador = 0

    for periodo in periodos:
        for curso in cursos:
            estudiantes = User.objects.filter(curso=curso, role='ESTUDIANTE')
            materias = curso.materias.all()

            for estudiante in estudiantes:
                for materia in materias:
                    # Componentes de evaluacion
                    ser = Decimal(str(round(random.uniform(6, 10), 2)))
                    saber = Decimal(str(round(random.uniform(20, 35), 2)))
                    hacer = Decimal(str(round(random.uniform(20, 35), 2)))
                    decidir = Decimal(str(round(random.uniform(6, 10), 2)))

                    auto_ser = Decimal(str(round(random.uniform(3, 5), 2)))
                    auto_decidir = Decimal(str(round(random.uniform(3, 5), 2)))

                    try:
                        Nota.objects.get_or_create(
                            estudiante=estudiante,
                            materia=materia,
                            periodo=periodo,
                            defaults={
                                'ser_puntaje': ser,
                                'saber_puntaje': saber,
                                'hacer_puntaje': hacer,
                                'decidir_puntaje': decidir,
                                'autoevaluacion_ser': auto_ser,
                                'autoevaluacion_decidir': auto_decidir,
                                'comentario': f"Notas para {estudiante.first_name} en {materia.nombre} ({periodo.nombre})"
                            }
                        )
                        contador += 1
                    except Exception as e:
                        print(f"Error al crear nota: {e}")

    print(f"Total notas: {contador}")


def poblar():
    # Verifica si hay cursos o estudiantes, ya que son prerequisitos para el poblamiento.
    if not Curso.objects.exists() or not User.objects.filter(role='ESTUDIANTE').exists():
        print("Error: No hay cursos o estudiantes en la base de datos. Por favor, crea algunos antes de poblar.")
        return

    with transaction.atomic():
        periodos = crear_periodos()
        fechas = generar_fechas_clase()
        cursos = Curso.objects.all()

        crear_asistencias(cursos, fechas)
        crear_participaciones(cursos, fechas)
        crear_notas(periodos, cursos)

    print("Poblamiento completado con exito")


# Esto asegura que la función poblar() solo se ejecute cuando el script es el programa principal.
if __name__ == '__main__':
    poblar()