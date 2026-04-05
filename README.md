# Saunier Duval MiGo — Home Assistant Integration

Integración no oficial para controlar tu caldera Saunier Duval a través de la app **MiGo** desde Home Assistant.

> Basada en la API interna de Netatmo Energy (plataforma subyacente de MiGo).

---

## ⚠️ Aviso importante: riesgo de baneo

Los servidores de MiGo/Netatmo **pueden bloquear tu cuenta** si haces demasiadas consultas en poco tiempo. El intervalo mínimo recomendado es **5 minutos**. Por defecto se consulta cada 60 minutos.

---

## Qué puedes hacer

- Ver la temperatura actual y el setpoint de tu termostato
- Ver la temperatura exterior (si tu módulo la expone)
- Activar o desactivar la caldera (modo en casa / modo ausente)

> **No es posible cambiar la temperatura desde HA.** La integración no soporta modificar el setpoint — solo permite activar o desactivar la caldera.

| Modo HVAC en HA | Equivalente en MiGo |
|---|---|
| `auto` | Estoy en casa — programa horario activo |
| `off` | Modo ausente |

Los datos de estado (temperatura, modo, caldera encendida/apagada) son atributos de la entidad climate. La caldera nunca se "apaga" del todo — en modo ausente baja al setpoint mínimo configurado en tu programa.

---

## Instalación via HACS

1. En HACS → Integraciones → ⋮ → **Repositorios personalizados**
2. URL: `https://github.com/moral3jo/home-assistant-migo`
3. Categoría: **Integración**
4. Pulsa **Añadir** → busca "MiGo" → **Descargar**
5. Reinicia Home Assistant
6. Ve a **Configuración → Dispositivos y servicios → Añadir integración** y busca **Saunier Duval MiGo**
7. Introduce tu email y contraseña de la app MiGo

---

## Uso

Una vez instalada y configurada, la integración crea un dispositivo con:

- **Entidad climate** — muestra temperatura actual, setpoint, modo y atributos extra (`boiler_firing`, `outdoor_temperature`). Desde aquí puedes cambiar entre modo activo y ausente.
- **Botón "Actualizar"** — fuerza una consulta inmediata a la API sin esperar el intervalo configurado.

### Cambiar el intervalo de actualización

Por defecto la integración consulta la API **cada 60 minutos**. Para cambiarlo:

`Configuración > Dispositivos y servicios > Saunier Duval MiGo > icono ⚙ (Configurar)`

Aparece un slider de 5 a 240 minutos. El cambio se aplica al momento sin reiniciar HA.

> No bajes de 5 minutos para evitar que Netatmo bloquee tu cuenta.

---

## Instalación manual

Copia la carpeta `custom_components/migo/` en tu directorio `<config>/custom_components/` y reinicia Home Assistant.

---

## Probar la API antes de instalar

Si quieres verificar que tus credenciales funcionan antes de instalar la integración:

```bash
python -m venv .venv
.venv/Scripts/pip install aiohttp   # Windows
# .venv/bin/pip install aiohttp     # Linux/Mac
python test_api.py
```

El script hace login, descarga la topología de tu casa y muestra el estado actual de la caldera. Opcionalmente puedes probar el cambio de modo.

---

## Notas técnicas

- La plataforma MiGo es una white-label de **Netatmo Energy**. Esta integración usa las credenciales de aplicación extraídas del APK oficial de MiGo. Son credenciales de la *app*, no tuyas — equivalen al "DNI" que la app usa ante los servidores de Netatmo. Tu email y contraseña solo se usan en el momento de configurar la integración.
- El intervalo de polling es configurable entre 5 y 240 minutos desde la interfaz de HA.

---

## Estado del proyecto

| Función | Estado |
|---|---|
| Login / reautenticación automática | ✅ |
| Ver temperatura actual y setpoint | ✅ |
| Ver temperatura exterior | ✅ |
| Activar / desactivar (modo ausente) | ✅ |
| Estado de la caldera (quemando o no) | ✅ |
| Botón de actualización manual | ✅ |
| Intervalo de polling configurable | ✅ |
| Cambiar temperatura desde HA | ❌ |
| Control por habitaciones | 🔜 |

---

## Disclaimer

Este proyecto no está afiliado ni respaldado por Saunier Duval ni por Netatmo. Úsalo bajo tu propia responsabilidad.
