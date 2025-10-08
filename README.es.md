# Sistema de Flujos de Trabajo Automatizados AAIS

> **Documentación multiidioma**: [English](README.md) | [中文](README.zh-CN.md) | [Español](README.es.md)

Sistema de flujos de trabajo de llamadas automatizadas impulsado por integración de VAPI y Smartsheet. Admite múltiples tipos de flujos de trabajo con programación inteligente y manejo de zonas horarias.

## Características

- **Soporte Multi-Flujo**: Recordatorios de cancelación, notificaciones de facturación y más
- **Sistema de Llamadas de 3 Etapas**: Secuencias de seguimiento automatizadas con asistentes de IA específicos por etapa
- **Programación Inteligente**: Cálculos de días hábiles con manejo automático del horario de verano
- **Llamadas por Lotes y Secuenciales**: Etapa 0 usa llamadas por lotes, etapas 1-2 usan llamadas secuenciales
- **Integración con Smartsheet**: Actualización automática de registros y seguimiento de llamadas
- **GitHub Actions**: Implementación sin servidor con ejecución diaria automatizada

## Estructura del Proyecto

```
.
├── config/              # Archivos de configuración
├── services/            # Servicios de API externos
│   ├── smartsheet_service.py
│   └── vapi_service.py
├── workflows/           # Flujos de trabajo empresariales
│   └── cancellations.py
├── utils/              # Funciones de utilidad
├── tests/              # Archivos de prueba
├── main.py             # Punto de entrada (cron job)
└── .env               # Variables de entorno
```

## Inicio Rápido

### 1. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 2. Configurar Variables de Entorno

Crear archivo `.env` (solo 2 variables requeridas):

```env
SMARTSHEET_ACCESS_TOKEN=tu_token
VAPI_API_KEY=tu_clave_vapi
```

**Otras configuraciones en `config/settings.py`**:
- IDs de hojas
- ID del número de teléfono de la empresa
- IDs de asistentes para cada etapa
- Número de teléfono de prueba

### 3. Ejecutar Pruebas

```bash
python3 tests/test_vapi_cancellation_flow.py
```

### 4. Ejecución Manual

```bash
python3 main.py
```

## Implementación

### ✅ Recomendado: GitHub Actions (Gratis y Automatizado)

¡El sistema está configurado con GitHub Actions - **no se requiere servidor**!

#### 1. Configurar Secretos de GitHub

En tu repositorio de GitHub:

1. Ve a **Settings** → **Secrets and variables** → **Actions**
2. Haz clic en **New repository secret**
3. Agrega estos secretos:
   - Nombre: `SMARTSHEET_ACCESS_TOKEN`, Valor: tu token de Smartsheet
   - Nombre: `VAPI_API_KEY`, Valor: tu clave de VAPI

#### 2. Habilitar GitHub Actions

1. Ve a la pestaña **Actions**
2. Busca "Daily Cancellation Workflow"
3. Haz clic en **Enable workflow** (si es necesario)

#### 3. Verificar Ejecución

- **Automático**: Se ejecuta diariamente a las 4:00 PM hora del Pacífico (manejo automático de horario de verano)
- **Manual**: Actions → Daily Cancellation Workflow → Run workflow
- **Ver registros**: Actions → Haz clic en cualquier ejecución para ver registros detallados

#### Manejo del Horario de Verano

El sistema maneja automáticamente las transiciones del horario de verano:
- El flujo de trabajo se activa a las **UTC 23:00 y UTC 00:00**
- El código Python verifica si es **4:00 PM hora del Pacífico**
- Solo se ejecuta durante la hora correcta
- ¡No se necesitan ajustes manuales!

**Nota**: Los trabajos programados de GitHub Actions pueden tener retrasos de 3-15 minutos. Esto es normal.

### Alternativa: Implementación en Servidor (No Recomendado)

<details>
<summary>Haz clic para expandir las instrucciones de implementación en servidor (solo para casos especiales)</summary>

#### 1. Subir Código

```bash
rsync -avz --exclude 'venv' --exclude '__pycache__' \
  . usuario@servidor:/opt/aais/python-read-write-sheet/
```

#### 2. Instalar Dependencias

```bash
ssh usuario@servidor
cd /opt/aais/python-read-write-sheet
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 3. Configurar Tarea Cron

```bash
crontab -e
```

Agregar:
```cron
0 16 * * * TZ=America/Los_Angeles cd /opt/aais/python-read-write-sheet && /opt/aais/python-read-write-sheet/venv/bin/python3 main.py >> logs/cron/output.log 2>&1
```

</details>

## Pruebas

Todos los archivos de prueba están en el directorio `tests/`:

- `test_vapi_cancellation_flow.py` - Prueba completa de extremo a extremo
- `test_followup_date_calculation.py` - Prueba de cálculo de fechas
- `cleanup_test_data.py` - Limpiar datos de prueba

## Detalles del Flujo de Trabajo

### Flujo de Ejecución Diaria

1. **4:00 PM Hora del Pacífico** - Activación automatizada
2. **Obtener Clientes** - Obtener clientes listos para llamadas hoy (`f_u_date` = hoy)
3. **Etapa 0 (1er Recordatorio)** - Llamadas por lotes de recordatorios iniciales
4. **Etapas 1-2 (2do-3er Recordatorios)** - Llamadas de seguimiento secuenciales
5. **Actualizar Registros** - Escribir resultados de llamadas y próximas fechas de seguimiento
6. **Verificación Manual** - La finalización de Etapa 3 requiere revisión manual
7. **Limpieza Automática** - Eliminar registros mayores de 30 días

### Reglas de Filtrado de Clientes

**Omitir cuando**:
- La casilla `done?` está marcada
- `company` está vacío
- `amount_due` está vacío
- `cancellation_date` está vacío
- `ai_call_stage >= 3` (secuencia de llamadas completa)

**Llamar cuando**:
- `f_u_date` (fecha de seguimiento) = hoy

### Proceso de 3 Etapas

#### **Etapa 0 → 1 (1er Recordatorio)**
- Smartsheet `ai_call_stage` = vacío o 0
- Usa `CANCELLATION_1ST_REMINDER_ASSISTANT_ID`
- **Llamadas por lotes** (todos los clientes simultáneamente)
- Próxima fecha F/U = actual + (días hábiles totales ÷ 3)
- Actualiza Smartsheet: `ai_call_stage = 1`

#### **Etapa 1 → 2 (2do Recordatorio)**
- Smartsheet `ai_call_stage = 1`
- Usa `CANCELLATION_2ND_REMINDER_ASSISTANT_ID`
- **Llamadas secuenciales** (una por una)
- Próxima fecha F/U = actual + (días hábiles restantes ÷ 2)
- Actualiza Smartsheet: `ai_call_stage = 2`

#### **Etapa 2 → 3 (3er Recordatorio)**
- Smartsheet `ai_call_stage = 2`
- Usa `CANCELLATION_3RD_REMINDER_ASSISTANT_ID`
- **Llamadas secuenciales** (una por una)
- Sin próxima fecha F/U
- Actualiza Smartsheet: `ai_call_stage = 3`
- **No marca automáticamente como completado** - espera verificación manual

### Cálculo de Días Hábiles

- Omite automáticamente los fines de semana (sábado/domingo)
- Las fechas F/U garantizadas caen en días hábiles
- Todos los cálculos de fechas excluyen los fines de semana

### Campos Actualizados

Después de cada llamada:
- `ai_call_stage`: +1
- `ai_call_summary`: Agrega resumen de llamada
- `ai_call_eval`: Agrega resultado de evaluación
- `f_u_date`: Próxima fecha de seguimiento (vacío después de Etapa 3)
- ~~`done?`~~: Marcado automático deshabilitado, espera revisión manual

## Registros

Los registros se almacenan en el directorio `logs/cron/`:
- `cancellations_AAAA-MM-DD.log` - Registros de ejecución diaria
- `output.log` - Salida de Cron
- Conservación automática durante 30 días

## Solución de Problemas

Ver registros:
```bash
tail -f logs/cron/output.log
```

Prueba manual:
```bash
source venv/bin/activate
python3 main.py
```

## Stack Tecnológico

- Python 3.8+
- API de Smartsheet
- API de VAPI
- GitHub Actions (flujos de trabajo programados)

## Licencia

Consulta el archivo [LICENSE](LICENSE) para obtener detalles.
