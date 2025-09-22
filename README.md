# RealTajoFCBack

Aplicación backend para procesar documentos PDF de clasificación y calendario.

## Requisitos

- Python 3.11+

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecución del servidor

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8765
```

El servidor quedará accesible desde el exterior (si la red lo permite) en el puerto `8765`.

## Endpoints disponibles

- `POST /classification/pdf`: subir un PDF de clasificación y almacenarlo como JSON.
- `GET /classification`: recuperar el último JSON de clasificación procesado.
- `POST /schedule/pdf`: subir un PDF de calendario y almacenarlo como JSON.
- `GET /schedule`: recuperar el último JSON de calendario procesado.

Cada petición `POST` devuelve el JSON generado a partir del PDF enviado.
