-- Estas consultas se ejecutan desde DBCode o Atlas SQL Interface.
-- Las colecciones dimensionales se consultan como tablas.

-- 1. Ventas por metodo de pago
SELECT metodo_pago, SUM(total_venta) AS total_ventas, COUNT(*) AS lineas
FROM fact_ventas
GROUP BY metodo_pago
ORDER BY total_ventas DESC
LIMIT 10;

-- 2. Ventas por ciudad y departamento
SELECT c.departamento, c.ciudad,
       SUM(f.total_venta) AS ingresos,
       SUM(f.ganancia_neta) AS ganancia
FROM fact_ventas f
JOIN dim_cliente c ON f.cliente_key = c.cliente_key
GROUP BY c.departamento, c.ciudad
ORDER BY ingresos DESC;

-- 3. Evolucion mensual
SELECT d.anio, d.mes,
       SUM(f.total_venta) AS ingresos,
       SUM(f.cantidad) AS unidades
FROM fact_ventas f
JOIN dim_fecha d ON f.fecha_key = d.fecha_key
GROUP BY d.anio, d.mes
ORDER BY d.anio, d.mes;

-- 4. Productos mas vendidos
SELECT p.categoria, p.nombre,
       SUM(f.cantidad) AS unidades,
       SUM(f.total_venta) AS ingresos
FROM fact_ventas f
JOIN dim_producto p ON f.producto_key = p.producto_key
GROUP BY p.categoria, p.nombre
ORDER BY unidades DESC
LIMIT 10;

-- 5. Validacion de volumen y relaciones
SELECT COUNT(*) AS filas_fact_ventas FROM fact_ventas;
SELECT COUNT(*) AS filas_dim_cliente FROM dim_cliente;
SELECT COUNT(*) AS filas_dim_producto FROM dim_producto;
SELECT COUNT(*) AS filas_dim_fecha FROM dim_fecha;