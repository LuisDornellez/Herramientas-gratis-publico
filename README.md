# OfiKit 1.3.3
Suite portable de oficina para Windows (un solo .exe).

## Cómo obtener el .exe
1. Sube el CONTENIDO de esta carpeta (no la carpeta) a un repositorio de GitHub, con estos archivos en la raíz: ofikit.py, requirements.txt, icon.ico, icon.png, README.md, .gitignore y .github/workflows/build.yml.
   Desde el celular GitHub no deja subir carpetas: crea build.yml con "Add file > Create new file", escribiendo en el nombre la ruta completa `.github/workflows/build.yml`, y pega su contenido.
2. Pestaña Actions > Build OfiKit > espera que termine (si falla, ahí se ve el error). Se ejecuta solo en cada push a main/master, o a mano con "Run workflow".
3. Ve a la sección **Releases** del repositorio y descarga `OfiKit.exe` del release "Última compilación" (etiqueta `exe-latest`, se reemplaza en cada compilación).

## Herramientas
PDF (unir, dividir, rotar, comprimir, imágenes a PDF, marca de agua, numerar, proteger/quitar contraseña), Imágenes, Renombrador, Presupuestos, Recetas (encadenar pasos y guardarlos), Carpeta vigilada, Buscar dentro de archivos, Orden de carpetas (por tipo, duplicados), Utilidades (contraseñas, QR, ocultar datos sensibles), Datos (unir CSV, quitar duplicados, CSV<->Excel), Calculadoras, Historial del portapapeles, Comparar documentos y Control de horas.

Las recetas (recetas.json) y las horas (horas.json) se guardan junto al .exe; si esa carpeta no permite escribir, en la carpeta OfiKit de tu usuario.

## Novedades 1.3.3
- Pie "Creado por:" con saberaclick.com y www.luisdornellez.com, clickeables, en el menú lateral.

## Novedades 1.3.2
- Las fotos del celular ya no salen giradas al reducir o convertir; los PNG con transparencia pasan a JPG/PDF con fondo blanco (antes quedaban negros).
- Montos con formato 1.234,56 o 1,234.56 en Calculadoras y Presupuestos.
- Buscar y Comparar: ya encuentran palabras partidas en Word (ej. "Fac" + "tura") y entienden & y acentos en Word/Excel.
- CSV con ; y decimales con coma pasan a Excel como números.
- Carpeta vigilada: detener e iniciar rápido ya no duplica la vigilancia.
- Control de horas: guarda el cliente y la nota del momento en que pulsaste Iniciar.
- recetas.json dañado: se guarda una copia .bak en vez de perder todo en silencio.
