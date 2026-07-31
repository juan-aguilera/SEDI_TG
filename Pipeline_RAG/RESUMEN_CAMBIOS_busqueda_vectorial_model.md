# Resumen de cambios — búsqueda vectorial conectada al grafo real (label Model)

Fecha: 2026-07-31

## Cuál era el problema

La parte del sistema que busca "por parecido" (búsqueda vectorial, para preguntas difusas que no
mencionan un nombre exacto) no estaba conectada a mi grafo real. Buscaba sobre datos de artículos
académicos que ya no existen en mi base de datos, usando credenciales que ni siquiera están
configuradas. En la práctica, esa parte del sistema no podía funcionar.

Mientras tanto, yo ya tengo, en mi grafo real, los modelos (`Model`) con sus vectores ya calculados
y un índice de búsqueda ya listo para usarse.

## Qué se hizo

Se conectó la búsqueda vectorial a mi grafo real, para que ahora sí busque entre los modelos (`Model`)
que ya tengo cargados, en vez de sobre datos que no existen.

En simple, los cambios fueron:

1. **El "buscador" ahora apunta a mi base de datos real**, no a una externa desconectada. Antes se
   intentaba conectar con datos y credenciales que no existen; ahora usa mi Neo4j y el índice de
   modelos que ya estaba creado.
2. **La forma de convertir la pregunta en un vector se corrigió** para que use el mismo método con el
   que se calcularon los vectores de mis modelos (Azure). Antes usaba un método distinto, lo que
   hubiera hecho que las comparaciones no tuvieran sentido (como comparar peras con manzanas).
3. **El modelo de lenguaje que redacta la respuesta final también se corrigió**, porque dependía de
   una credencial que no tengo configurada. Ahora usa la misma configuración de Azure que ya uso en
   el resto del sistema.
4. **La información que se guarda de cada resultado encontrado se simplificó y se corrigió.** Antes
   el sistema esperaba datos de "artículos" (título, id de artículo) que un modelo no tiene. Ahora
   guarda lo que sí tiene sentido para un modelo: su identificador y su tipo (`Model`).
5. **Se corrigió un nombre interno inconsistente** que ya traía un error de fondo: el sistema usaba
   una "casilla" de datos con un nombre en el código, y la documentación oficial de esa misma casilla
   tenía otro nombre distinto — ahora coinciden.

## Qué queda pendiente (a propósito, no se tocó en esta tanda)

- Esto solo se implementó para modelos (`Model`). Extenderlo a los demás tipos de datos que tengo
  (datasets, spaces, repositorios, etc.) es un trabajo aparte, ya planificado por separado.
- El paso final del flujo (el que arma la consulta a la base de datos "con contexto", después de la
  búsqueda vectorial) todavía no sabe interpretar bien los identificadores reales de mis modelos —
  sigue entrenado con ejemplos de artículos académicos. Es un trabajo pendiente distinto, ya
  documentado.

## Cómo se verificó

Se revisó que todo el código compila y se ejecuta sin errores de programación hasta el punto de
conectarse a la base de datos. La conexión final no se pudo probar de punta a punta porque, al
momento de hacer el cambio, mi Neo4j local no estaba encendido — falta correr una prueba real con la
base de datos activa para confirmar que trae resultados correctos.
