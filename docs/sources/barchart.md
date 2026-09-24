# Barchart — https://www.barchart.com/

- **Finalidad:** históricos, indicadores y eventos mediante productos con permiso.
- **Modalidad:** el sitio web prohíbe la extracción automatizada. El único acceso automatizado previsto es **Barchart OnDemand**, un producto de pago: el adaptador `terminal/adaptadores/proveedores.py::Barchart` requiere `BARCHART_API_KEY` y contrato.
- **Cobertura:** **no confirmada para BMV local ni SIC**. Hasta que el contrato indique cobertura de la BMV, su latencia, moneda y serie, queda como proveedor **complementario** para los mercados de EE. UU. que sí cubre. No puede verificar la cobertura de un instrumento del simulador (ver `docs/cobertura.md`).
- **Estado:** pendiente de contrato. Sin llamadas.
- **Sello temporal:** 2026-09-23.
