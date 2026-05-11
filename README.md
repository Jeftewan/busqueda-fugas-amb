# 💧 Seguimiento de Fugas — Acueducto

Sistema local para el seguimiento, priorización y gestión de fugas detectadas en el contrato de búsqueda de fugas del acueducto. Opera sobre el archivo Excel `AMB_1.xlsx` actualizado diariamente por el contratista.

---

## 1. Descripción

La aplicación permite:
- Importar el Excel diario con datos de fugas, cuadrillas y POIs pendientes
- Calcular automáticamente la prioridad de cada fuga (ALTA/MEDIA/BAJA) con base en tipo de red, palabras clave en comentarios y antigüedad
- Gestionar estados internos y órdenes de trabajo (OT)
- Visualizar fugas en mapa interactivo con detección de clusters geográficos
- Enviar correos con PDF adjunto al equipo de mantenimiento
- Generar reportes ejecutivos PDF descargables

---

## 2. Requisitos

- Python 3.10 o superior ([python.org](https://www.python.org/downloads/))
- Conexión a internet (solo para envío de correos y primera instalación de dependencias)
- Cuenta Gmail con verificación en 2 pasos (para envío de correos)

---

## 3. Instalación (primera vez)

### En Windows:
1. Instalar Python 3.10+ desde [python.org](https://www.python.org/downloads/)
2. Descomprimir la carpeta `seguimiento-fugas`
3. Doble clic en `run.bat`
4. Esperar a que se abra el navegador en `http://localhost:8501`

### En Linux/Mac:
```bash
chmod +x run.sh
./run.sh
```

---

## 4. Configurar Gmail App Password

Para enviar correos desde la aplicación:

1. Activar verificación en 2 pasos en su cuenta Gmail
2. Ir a [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Crear una nueva App Password para "Correo" → "Otro (nombre personalizado)"
4. Copiar la contraseña de 16 caracteres
5. Ingresar en la app: página **⚙️ Configuración** → pestaña SMTP

---

## 5. Cómo arrancar

- **Windows:** Doble clic en `run.bat`
- **Linux/Mac:** `./run.sh`
- La app abre automáticamente en el navegador en `http://localhost:8501`

---

## 6. Cómo cargar el Excel diario

1. Recibir el archivo `AMB_1.xlsx` actualizado del contratista
2. En la app, ir a **📥 Cargar Excel**
3. Hacer clic en "Seleccione el archivo Excel" y elegir el archivo
4. Hacer clic en **🚀 Importar**
5. Verificar el resumen de cambios (nuevos, modificados, reparados, discrepancias)

**Importante:** El sistema nunca pierde datos internos (prioridades manuales, OT, notas) al reimportar.

---

## 7. Tour de las páginas

| Página | Descripción |
|---|---|
| 🏠 Home | Hub operativo con 4 KPIs del día (críticas, OTs por generar, reparadas en la semana, backlog estimado) y 4 acciones rápidas. |
| 📊 Dashboard | 6 KPIs en grid 3×2, card visual de backlog con barra de progreso, gráficos con narrativa. Top 10 críticas con click en fila para ver detalle. |
| 💧 Fugas | **Modo lectura por defecto** con selección multi-fila nativa para acciones masivas. Toggle "Modo edición" para cambiar prioridades manuales. Detalle organizado en 5 tabs (Resumen, OT, Notas, Historial, Mapa). |
| 🗺️ Mapa | Markers por prioridad, leyenda flotante, **panel lateral** que muestra detalle al clickear, selector de capa base (Calles / Satélite / Oscuro), clusters geográficos. |
| 👷 Cuadrillas | **Cards comparativas con barras visuales** lado a lado (AMB1 vs AMB2), filtro de rango de fechas, **heatmap semanal** de productividad. |
| 📥 Cargar Excel | **Vista previa** de las 3 hojas antes de importar, validación previa, resumen visual con cards de colores (nuevos/modificados/discrepancias). |
| 📧 Correos | **Wizard de 3 pasos** (Tipo → Fugas → Confirmar), preview HTML del correo en tab separado, historial con detalle. |
| ⚙️ Configuración | Banner de onboarding si SMTP no está configurado, sliders con tooltips explicativos, prueba de envío con feedback específico según el error. |

### 💡 Identidad visual

La app utiliza una paleta corporativa azul agua y la tipografía Inter:

- **Primario:** azul agua `#0B6E99`
- **Acento:** turquesa `#00A896`
- **Semáforo de prioridad:** rojo coral `#D7263D` (ALTA), naranja `#F46036` (MEDIA), verde `#2EB872` (BAJA)
- **Toda la app** usa cards con bordes redondeados, sombras sutiles y estados hover.

---

## 8. Troubleshooting

**Puerto 8501 ocupado:**
```bash
streamlit run app.py --server.port 8502
```

**Error SMTP "Authentication failed":**
- Verificar que el App Password tenga exactamente 16 caracteres
- Verificar que la verificación en 2 pasos esté activa en la cuenta Gmail
- Usar App Password, no la contraseña normal de Gmail

**Archivo Excel con error al importar:**
- Verificar que el archivo tenga las 3 hojas: `Collected Data`, `Crew Performance`, `Remaining Pois`
- No abrir el archivo en Excel al mismo tiempo que se importa

**La app no abre el navegador:**
- Abrir manualmente [http://localhost:8501](http://localhost:8501)

---

## 9. Respaldo de la base de datos

La base de datos SQLite está en `data/fugas.db`. Para respaldar:

```bash
# Copiar el archivo a una ubicación segura
cp data/fugas.db backups/fugas_$(date +%Y%m%d).db
```

Se recomienda hacer respaldo después de cada carga de Excel importante.

Los archivos Excel importados quedan archivados automáticamente en `data/excel_archive/`.

---

## Stack técnico

- **Streamlit** — interfaz web local
- **SQLite** — base de datos local (sin servidor)
- **pandas / openpyxl** — lectura del Excel
- **folium / streamlit-folium / branca** — mapa interactivo y leyenda flotante
- **Plotly** — gráficos interactivos
- **reportlab** — generación de PDFs
- **smtplib** — envío de correos (stdlib Python)
- **Inter (Google Fonts)** — tipografía corporativa
