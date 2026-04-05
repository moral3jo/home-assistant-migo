# Saunier Duval MiGo — Home Assistant Integration

Integración no oficial para controlar tu caldera Saunier Duval a través de la app **MiGo** desde Home Assistant.

> Basada en la API interna de Netatmo Energy (plataforma subyacente de MiGo).

---

## ⚠️ Aviso importante: riesgo de baneo

Los servidores de MiGo/Netatmo **pueden bloquear tu cuenta** si haces demasiadas consultas en poco tiempo. Esta integración está configurada para consultar el estado **una vez cada hora**. No reduzcas este intervalo sin haberlo probado con cuidado.

---

## Qué puedes hacer

- Ver la temperatura actual y el setpoint de tu termostato
- Ver si la caldera está quemando en ese momento (`boiler_firing`)
- Cambiar entre **modo estoy en casa** (programa activo) y **modo ausente**

| Modo HVAC en HA | Equivalente en MiGo |
|---|---|
| `auto` | Estoy en casa / programa horario activo |
| `off` | Modo ausente |

---

## Instalación via HACS

1. En HACS → Integraciones → ⋮ → **Repositorios personalizados**
2. URL: `https://github.com/moral3jo/home-assistant-migo`
3. Categoría: **Integración**
4. Pulsa **Añadir** → busca "MiGo" → **Descargar**
5. Reinicia Home Assistant
6. Ve a **Ajustes → Integraciones → Añadir integración** y busca **Saunier Duval MiGo**
7. Introduce tu email y contraseña de la app MiGo

---

## Uso

Una vez instalada y configurada, la integración crea un dispositivo con:

- **Entidad climate** — muestra temperatura actual, setpoint y modo (auto/off). Desde aquí puedes cambiar entre modo activo y ausente.
- **Botón "Actualizar"** — fuerza una consulta inmediata a la API sin esperar el intervalo configurado.

### Cambiar el intervalo de actualización

Por defecto la integración consulta la API **cada 60 minutos**. Para cambiarlo:

`Configuración > Dispositivos y servicios > Saunier Duval MiGo > icono ⚙ (Configurar)`

Aparece un slider de 5 a 240 minutos. El cambio se aplica al momento sin reiniciar HA.

> No bajes de 5 minutos para evitar que Netatmo bloquee tu cuenta.

### Temperatura exterior

La temperatura exterior (si tu módulo la expone) aparece como atributo extra de la entidad climate. Puedes mostrarla en el dashboard con una tarjeta de tipo **Entidad** apuntando al atributo `outdoor_temperature`.

---

## Instalación manual

Copia la carpeta `custom_components/migo/` en tu directorio `<config>/custom_components/` y reinicia Home Assistant.

---

## Probar la API antes de instalar

Si quieres verificar que tus credenciales funcionan antes de instalar la integración:

```bash
pip install aiohttp
python test_api.py
```

El script hace login, descarga la topología de tu casa y muestra el estado actual de la caldera. Opcionalmente puedes probar el cambio de modo.

---

## Notas técnicas

- La plataforma MiGo es una white-label de **Netatmo Energy**. Esta integración usa las credenciales de aplicación extraídas del APK oficial de MiGo. Son credenciales de la *app*, no tuyas — equivalen al "DNI" que la app usa ante los servidores de Netatmo. Tu email y contraseña solo se usan en el momento de configurar la integración.
- El intervalo de polling por defecto es **60 minutos** y se puede cambiar desde la interfaz de HA sin tocar código (ver sección Uso).

---

## Estado del proyecto

| Función | Estado |
|---|---|
| Login / reautenticación automática | ✅ |
| Ver temperatura actual y setpoint | ✅ |
| Modo ausente / estoy en casa | ✅ |
| Ver si la caldera está quemando | ✅ |
| Control por habitaciones | 🔜 |
| Sensor de temperatura independiente | 🔜 |

---

## Disclaimer

Este proyecto no está afiliado ni respaldado por Saunier Duval ni por Netatmo. Úsalo bajo tu propia responsabilidad.
