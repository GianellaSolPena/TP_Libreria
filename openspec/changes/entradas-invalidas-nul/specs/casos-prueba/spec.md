# Spec Delta

## ADDED Requirements

### Requirement: Caso extra de RN-15 con carácter nulo
`parcial/test/` SHALL incluir un archivo `.http` extra (no es un caso C del PDF, no lleva número C) que demuestre RN-15 con textos que contienen U+0000, con las mismas convenciones que los demás archivos: precondiciones al comienzo, ejecutable tras `python seed.py`, `# @no-cookie-jar` y `Cookie:` por sesión, y la respuesta esperada en un comentario junto a cada petición. MUST cubrir al menos la búsqueda `GET /libros?titulo=a%00b`, el login con U+0000 en el correo y un alta con sesión de ADMIN con U+0000 en un texto, todos con 422, y una petición de control válida que siga respondiendo como antes.

#### Scenario: Corrida del caso extra
- **WHEN** tras `python seed.py` y con el servidor arriba se corren en orden todas las peticiones del archivo
- **THEN** cada una responde con el código del comentario: 422 para las entradas con U+0000 y el código habitual para la petición de control, y ninguna responde 500
