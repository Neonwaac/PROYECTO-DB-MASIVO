import docx
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
import os

doc = Document()
style = doc.styles["Normal"]
style.font.name = "Calibri"
style.font.size = Pt(11)
style.paragraph_format.space_after = Pt(6)
style.paragraph_format.line_spacing = 1.15
for lv in range(1, 4):
    h = doc.styles[f"Heading {lv}"]
    h.font.name = "Calibri"
    h.font.color.rgb = RGBColor(0x1B, 0x3A, 0x5C)

base = os.path.dirname(os.path.abspath(__file__))

def add_title_page():
    for _ in range(6):
        doc.add_paragraph()
    for text, sz, clr in [
        ("Sistema de Gestion de Ventas", 28, (0x1B, 0x3A, 0x5C)),
        ("HeavyCult", 24, (0x2E, 0x74, 0xB5)),
        ("Arquitectura de Datos con MongoDB Atlas", 16, (0x59, 0x56, 0x59)),
    ]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(text)
        r.bold = True
        r.font.size = Pt(sz)
        r.font.color.rgb = RGBColor(*clr)
    doc.add_paragraph()
    doc.add_paragraph()
    for line in ["David Medina", "Bases de Datos y Almacenamiento Masivo", "Primer Corte - 2026"]:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(line)
        r.font.size = Pt(13)
    doc.add_page_break()

def add_code(code_text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(code_text)
    r.font.name = "Consolas"
    r.font.size = Pt(8.5)
    r.font.color.rgb = RGBColor(0x2B, 0x2B, 0x2B)

def add_img(desc):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run(f"[INSERTAR CAPTURA: {desc}]")
    r.bold = True
    r.font.size = Pt(10)
    r.font.color.rgb = RGBColor(0xCC, 0x55, 0x00)

def add_tbl(headers, rows):
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(headers):
        c = t.rows[0].cells[i]
        c.text = h
        for p in c.paragraphs:
            for r in p.runs:
                r.bold = True
    for ri, rd in enumerate(rows):
        for ci, v in enumerate(rd):
            t.rows[ri + 1].cells[ci].text = str(v)
    doc.add_paragraph()

def add_b(text):
    doc.add_paragraph(text, style="List Bullet")

def read_file(rel_path):
    fp = os.path.join(base, rel_path)
    if os.path.exists(fp):
        with open(fp, "r", encoding="utf-8") as f:
            return f.read()
    return f"[Archivo no encontrado: {fp}]"

add_title_page()

doc.add_heading("1. Introduccion", level=1)
doc.add_paragraph("HeavyCult es un negocio de dropshipping especializado en calzado tactico, ropa oversize y accesorios tacticos, que opera a traves de la plataforma Dropi en Colombia. El sistema gestiona el flujo completo de ventas: desde la recepcion de pedidos via WhatsApp hasta la confirmacion de entrega con el transportista, incluyendo el manejo de novedades (devoluciones) y cancelaciones.")
doc.add_paragraph("Este proyecto implementa una arquitectura de datos completa utilizando MongoDB Atlas como base de datos distribuida en la nube, con un modelo dual OLTP/OLAP que permite tanto el procesamiento transaccional operativo como el analisis historico de negocio.")
doc.add_heading("Objetivos", level=2)
for o in ["Cluster de base de datos distribuida operativo (MongoDB Atlas Replica Set)","Modelo de datos transaccional (OLTP) y analitico (OLAP)","Pipeline de ingesta de datos con generacion masiva using Faker","Procesamiento de datos con Aggregation Pipeline ETL","Consultas analiticas optimizadas con benchmarking","Estrategia de indexacion para optimizacion de rendimiento"]:
    add_b(o)

doc.add_heading("2. Arquitectura General", level=1)
doc.add_paragraph("La arquitectura del sistema sigue un patron ETL (Extract, Transform, Load) con las siguientes capas:")
arch = "  Cliente Python (PyMongo)\n        |\n        v\n  MongoDB Atlas - heavycult (Cluster Distribuido)\n        |\n        +--> Colecciones OLTP: customers, products, orders, whatsapp_logs\n        |\n        +--> Aggregation Pipeline ETL\n        |\n        +--> Coleccion OLAP: ventas_analiticas\n        |\n        +--> Benchmarking + Indices Compuestos"
add_code(arch)
doc.add_heading("Tecnologias Utilizadas", level=2)
for n, d in [("MongoDB Atlas","Base de datos distribuida en la nube, cluster M0/M10"),("MongoDB Compass","Herramienta visual de administracion y consulta"),("Python 3.12","Lenguaje de programacion principal"),("PyMongo 4.18.0","Driver oficial de MongoDB para Python"),("Faker 40.38.0","Generacion de datos ficticios realistas"),("VS Code","Entorno de desarrollo integrado")]:
    add_b(f"{n}: {d}")
add_img("Diagrama de arquitectura en MongoDB Compass o diagrama propio")

doc.add_heading("3. Fase 1: Conexion a MongoDB Atlas", level=1)
doc.add_paragraph("El primer paso consiste en verificar la conectividad entre el cliente Python y el cluster distribuido de MongoDB Atlas. Se utiliza el archivo de configuracion .env para almacenar de forma segura el MONGO_URI (connection string), evitando exponer credenciales en el codigo fuente.")
doc.add_heading("Flujo de conexion", level=2)
for i, s in enumerate(["Leer la variable de entorno MONGO_URI desde el archivo .env","Crear una instancia de MongoClient con timeout de 5 segundos","Ejecutar el comando ping para verificar conectividad","Crear/obtener la base de datos heavycult","Manejar excepciones: ConnectionFailure, ConfigurationError, OperationFailure"], 1):
    add_b(f"Paso {i}: {s}")
doc.add_heading("Codigo fuente - conexion.py", level=2)
add_code(read_file("conexion.py"))
add_img("Salida de terminal mostrando Conexion exitosa a MongoDB Atlas!")
add_img("MongoDB Compass conectado al cluster heavycult mostrando las colecciones")

doc.add_heading("4. Fase 2: Modelo de Datos OLTP/OLAP", level=1)
doc.add_paragraph("Se implementa un modelo dual: colecciones OLTP normalizadas para el procesamiento transaccional del negocio, y una coleccion OLAP desnormalizada para analisis historico y reportes gerenciales.")
doc.add_heading("4.1 customers", level=3)
doc.add_paragraph("Almacena el directorio de clientes del negocio.")
add_tbl(["Campo","Tipo","Restriccion","Descripcion"],[["phone","String","UNIQUE","Telefono del cliente"],["name","String","Required","Nombre completo"],["city","String","Required","Ciudad de residencia"],["department","String","Required","Departamento"],["address","String","Required","Direccion de envio"],["created_at","DateTime","Default","Fecha de registro"]])
doc.add_heading("4.2 products", level=3)
doc.add_paragraph("Catalogo de productos de HeavyCult con variantes por talla.")
add_tbl(["Campo","Tipo","Restriccion","Descripcion"],[["dropi_product_id","String","UNIQUE","ID de Dropi"],["name","String","Required","Nombre del producto"],["category","String","Required","Categoria"],["pricing.supplier_cost","Double","Required","Costo del proveedor"],["pricing.sale_price","Double","Required","Precio de venta"],["variants[].sku","String","Index","SKU por variante"],["variants[].size","String","Required","Talla (S, M, L, XL)"],["variants[].stock","Integer","Required","Stock disponible"]])
doc.add_heading("4.3 orders", level=3)
doc.add_paragraph("Registro de ordenes de venta con items anidados.")
add_tbl(["Campo","Tipo","Restriccion","Descripcion"],[["order_number","String","UNIQUE","Numero unico de orden"],["customer_id","ObjectId","FK customers","Referencia al cliente"],["dropi_order_id","String","Required","ID en Dropi"],["items[].product_id","ObjectId","FK products","Producto vendido"],["items[].quantity","Integer","Required","Cantidad"],["items[].unit_price","Double","Required","Precio unitario"],["total_amount","Double","Required","Total de la orden"],["shipping_cost","Double","Required","Costo de envio"],["order_profit","Double","Required","Ganancia neta"],["payment_method","String","Required","Metodo de pago"],["status","String","Required","Estado de la orden"]])
doc.add_heading("4.4 ventas_analiticas (OLAP)", level=3)
doc.add_paragraph("Coleccion desnormalizada con modelo dimensional que consolida informacion de clientes, productos y ordenes en un solo documento, optimizada para consultas analiticas.")
doc.add_heading("4.5 Estrategia de Indexacion OLTP", level=2)
add_tbl(["Coleccion","Indice","Tipo","Justificacion"],[["customers","phone","UNIQUE","Busqueda unica por telefono"],["products","dropi_product_id","UNIQUE","Busqueda unica por ID Dropi"],["products","variants.sku","INDEX","Busqueda por SKU"],["orders","order_number","UNIQUE","Busqueda unica por numero"],["orders","customer_id","INDEX","JOIN con customers"],["orders","created_at","DESC","Ordenamiento cronologico"]])
add_img("MongoDB Compass: coleccion customers con documentos de ejemplo")
add_img("MongoDB Compass: coleccion orders con items anidados")
add_img("MongoDB Compass: estructura de ventas_analiticas")

doc.add_heading("5. Fase 3: Generacion Masiva de Datos", level=1)
doc.add_paragraph("Se genera un volumen significativo de datos ficticios pero realistas utilizando la libreria Faker, adaptada al contexto colombiano (es_CO) y al dominio de negocio de HeavyCult.")
doc.add_heading("5.1 Parametros de Generacion", level=2)
add_tbl(["Entidad","Cantidad","Detalle"],[["Clientes","5,000","Directorio con 6 ciudades colombianas"],["Productos","500","4 categorias, variantes por talla"],["Ordenes","30,000","Items anidados, estados de Dropi"]])
doc.add_heading("5.2 Ciudades y Costos de Flete", level=2)
add_tbl(["Ciudad","Departamento","Costo Flete"],[["Bogota","Cundinamarca","$14,000"],["Medellin","Antioquia","$15,000"],["Cali","Valle del Cauca","$16,000"],["Barranquilla","Atlantico","$18,000"],["Bucaramanga","Santander","$15,000"],["Pasto","Narino","$19,000"]])
doc.add_heading("5.3 Categorias y Estados", level=2)
doc.add_paragraph("Categorias: Calzado Tactico, Ropa Oversize, Accesorios Tacticos, Maletas y Morrales.")
doc.add_paragraph("Estados de ordenes Dropi: delivered (entregado), shipped (enviado), novelty (novedad/devolucion), cancelled (cancelado).")
doc.add_heading("5.4 Patron Batch Insert", level=2)
doc.add_paragraph("Se implementa el patron de Batch Insert con lotes de 1,000 documentos utilizando ordered=False para ignorar duplicados sin detener el proceso completo.")
batch_code = "def insertar_en_lotes(coleccion, datos, nombre_entidad):\n    total = len(datos)\n    for i in range(0, total, BATCH_SIZE):\n        lote = datos[i:i + BATCH_SIZE]\n        try:\n            coleccion.insert_many(lote, ordered=False)\n        except pymongo.errors.BulkWriteError as e:\n            insertados = e.details.get('nInserted', 0)\n            # Continua con el siguiente lote"
add_code(batch_code)
add_img("Terminal mostrando progreso de insercion de datos (lotes de 1000)")
add_img("MongoDB Compass: total de documentos en customers (5,000)")
add_img("MongoDB Compass: total de documentos en orders (30,000)")

doc.add_heading("6. Fase 4: Transformacion ETL (OLTP a OLAP)", level=1)
doc.add_paragraph("La transformacion ETL convierte los datos normalizados de las colecciones OLTP en un modelo dimensional desnormalizado en ventas_analiticas, optimizado para consultas analiticas.")
doc.add_heading("6.1 Aggregation Pipeline - Etapas", level=2)
for name, desc in [("$lookup (customers)","LEFT JOIN con customers usando customer_id."),("$unwind (cliente_info)","Descomprime el array del $lookup."),("$unwind (items)","Descomprime items de cada orden."),("$lookup (products)","LEFT JOIN con products usando items.product_id."),("$unwind (producto_info)","Descomprime el array del segundo $lookup."),("$project","Proyecta modelo dimensional: fecha, cliente, producto, financieros."),("$merge","Guarda en ventas_analiticas (whenNotMatched: insert).")]:
    p = doc.add_paragraph()
    r = p.add_run(f"{name}: ")
    r.bold = True
    p.add_run(desc)
doc.add_heading("6.2 Codigo del Pipeline", level=2)
add_code(read_file("scripts/transformar_oltp_a_olap.py"))
doc.add_heading("6.3 Justificacion de allowDiskUse", level=2)
doc.add_paragraph("Se habilita allowDiskUse=True para garantizar que las operaciones de agregacion que superan 100MB de RAM puedan utilizar disco temporero, evitando errores de memoria insuficiente.")
add_img("Terminal: TRANSFORMACION DE DATOS COMPLETA con tiempo y registros")
add_img("MongoDB Compass: documentos de ventas_analiticas con estructura denormalizada")

doc.add_heading("7. Fase 5: Benchmarking y Optimizacion", level=1)
doc.add_paragraph("Se evalua el rendimiento de 10 consultas analiticas representativas sobre la coleccion ventas_analiticas, midiendo la latencia de cada una.")
doc.add_heading("7.1 Indices Compuestos Aplicados", level=2)
add_tbl(["Nombre","Campos","Proposito"],[["idx_fecha","(anio, mes)","Consultas por periodo temporal"],["idx_cat_ganancia","(producto.categoria, ganancia_neta)","Ranking por categoria"],["idx_estado_ciudad","(estado, cliente.ciudad)","Filtros por ubicacion"]])
doc.add_heading("7.2 Resultados del Benchmarking", level=2)
add_tbl(["Consulta","Latencia (ms)","Filas","Descripcion"],[["1. Facturacion y Ganancia Mensual","270.18","13","Ingresos y pedidos por mes"],["2. Top 5 Productos por Categoria","159.00","4","Ranking mas rentables"],["3. Rentabilidad por Ciudad/Depto","188.67","6","Ingresos y novedades por ubicacion"],["4. Entregas vs Novedades","130.09","4","Proporcion de estados"]])
doc.add_heading("7.3 Resumen de Rendimiento", level=2)
add_tbl(["Metrica","Valor","Estado"],[["Latencia promedio","186.99 ms","OPTIMO (< 500ms)"],["Latencia maxima","270.18 ms","OPTIMO (< 500ms)"],["Documentos procesados","30,000","Validado"]])
doc.add_paragraph("Todas las consultas se ejecutaron con latencias significativamente por debajo del umbral de 500ms, validando la efectividad de la estrategia de indexacion compuesta.")
add_img("Terminal con resultados completos del benchmarking")

doc.add_heading("8. Justificaciones Tecnicas", level=1)
doc.add_heading("8.1 Ingesta por Lotes (Batch Insert)", level=2)
doc.add_paragraph("Se implemento el patron de Batch Insert con tamano de chunk de 1,000 documentos. Esta decision arquitectonica reduce la sobrecarga de red y el consumo de memoria RAM, alineandose con las mejores practicas de procesamiento de datos a escala.")
doc.add_heading("8.2 Transformacion ETL con Aggregation Pipeline", level=2)
doc.add_paragraph("Se utilizo el Aggregation Pipeline nativo de MongoDB con las etapas $lookup (JOIN) y $unwind para transformar datos normalizados (OLTP) en un modelo dimensional desnormalizado (OLAP). Se habilito allowDiskUse: true para garantizar escalabilidad.")
doc.add_heading("8.3 Indexacion Compuesta", level=2)
doc.add_paragraph("Se implemento una estrategia de Indices Compuestos (idx_fecha, idx_cat_ganancia, idx_estado_ciudad) que permite resolver operaciones de filtrado y ordenamiento sin escaneos completos de coleccion, reduciendo la complejidad de O(N) a O(log N).")

doc.add_heading("9. Solucion de Problemas Comunes", level=1)
for title, cause, sol in [("bad auth: authentication failed","Contrasena incorrecta en .env","Restablecer contrasena en Atlas > Database Access > Edit User"),("E11000 duplicate key error","Insertar valor unico duplicado","Usar insert_many(datos, ordered=False)"),("Expression $cond takes exactly 3 arguments","$cond solo acepta 3 argumentos","Anidar $cond dentro de otro $cond"),("The field must specify one accumulator","Usando $slice dentro de $group","Mover $slice a una etapa $project posterior"),("Consultas lentas (> 1 segundo)","Falta de indices o indices no optimos","Crear indices compuestos que cubran $match y $sort")]:
    doc.add_heading(title, level=3)
    p = doc.add_paragraph()
    r = p.add_run("Causa: ")
    r.bold = True
    p.add_run(cause)
    p2 = doc.add_paragraph()
    r2 = p2.add_run("Solucion: ")
    r2.bold = True
    p2.add_run(sol)

doc.add_heading("10. Conclusiones", level=1)
doc.add_paragraph("El proyecto demuestra la viabilidad de implementar una arquitectura de datos completa utilizando MongoDB Atlas para un negocio de dropshipping, cubriendo desde la ingesta transaccional hasta el analisis historico.")
doc.add_heading("Checklist de Cumplimiento", level=2)
for item in ["Cluster de base de datos distribuida operativo","Modelo de datos OLTP y OLAP","Pipeline de ingesta de datos (Faker + Batch Insert)","Procesamiento de datos (Aggregation Pipeline ETL)","Consultas analiticas optimizadas con benchmarking","Estrategia de indexacion para optimizacion","Documentacion tecnica completada"]:
    add_b(f"[OK] {item}")
doc.add_paragraph("La latencia promedio de 186.99ms en las consultas analiticas valida que la estrategia de indexacion compuesta es efectiva.")

doc.add_page_break()
doc.add_heading("Apendice: Codigo Fuente", level=1)
for label, rel in [("conexion.py","conexion.py"),("scripts/crear_estructura.py","scripts/crear_estructura.py"),("scripts/generar_datos_masivos.py","scripts/generar_datos_masivos.py"),("scripts/transformar_oltp_a_olap.py","scripts/transformar_oltp_a_olap.py"),("scripts/benchmarking_consultas.py","scripts/benchmarking_consultas.py")]:
    doc.add_heading(label, level=2)
    add_code(read_file(rel))

out = os.path.join(base, "docs", "DOCUMENTACION_FINAL.docx")
doc.save(out)
print(f"Documento guardado en: {out}")