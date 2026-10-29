import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import boto3
import pyarrow.parquet as parquet
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")
DATA_LAKE_ROOT = BASE_DIR / os.getenv("DATA_LAKE_ROOT", "data_lake")
DEFAULT_BUCKET = "abp-data-lake-neonwaac-2026"
DEFAULT_PREFIX = "heavycult"
DEFAULT_REGION = "us-east-1"
DEFAULT_PROFILE = "heavycult"


def sha256_archivo(ruta):
    digest = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            digest.update(bloque)
    return digest.hexdigest()


def descubrir_parquets():
    archivos = sorted(DATA_LAKE_ROOT.rglob("*.parquet"))
    if not archivos:
        raise FileNotFoundError(
            f"No se encontraron Parquet en {DATA_LAKE_ROOT}. "
            "Ejecuta primero python data_lake.py."
        )
    return archivos


def validar_parquet(ruta):
    metadata = parquet.ParquetFile(ruta).metadata
    return {
        "filas": metadata.num_rows,
        "columnas": metadata.num_columns,
        "bytes": ruta.stat().st_size,
        "sha256": sha256_archivo(ruta),
    }


def crear_cliente_s3(region=None, profile=None):
    session = boto3.Session(profile_name=profile, region_name=region)
    return session.client("s3"), session.region_name


def subir_archivos(s3, bucket, prefix, archivos, verificar):
    manifiesto = []
    for ruta in archivos:
        relativo = ruta.relative_to(DATA_LAKE_ROOT).as_posix()
        clave = "/".join(parte for parte in (prefix.strip("/"), relativo) if parte)
        info = validar_parquet(ruta)
        print(f"[S3] Validando {relativo}: {info['filas']:,} filas, {info['bytes']:,} bytes")
        s3.upload_file(
            str(ruta),
            bucket,
            clave,
            ExtraArgs={
                "ContentType": "application/octet-stream",
                "ServerSideEncryption": "AES256",
            },
        )
        if verificar:
            remoto = s3.head_object(Bucket=bucket, Key=clave)
            if remoto["ContentLength"] != info["bytes"]:
                raise RuntimeError(f"Tamano remoto diferente para s3://{bucket}/{clave}")
        info.update({"archivo_local": relativo, "s3_uri": f"s3://{bucket}/{clave}"})
        manifiesto.append(info)
        print(f"[S3] Subido: s3://{bucket}/{clave}")
    return manifiesto


def publicar_data_lake(bucket, prefix, region, profile, verificar):
    if not bucket:
        raise ValueError("Indica --bucket o configura S3_BUCKET en .env.")
    archivos = descubrir_parquets()
    s3, region_real = crear_cliente_s3(region, profile)
    s3.head_bucket(Bucket=bucket)
    manifiesto = subir_archivos(s3, bucket, prefix, archivos, verificar)
    clave_manifiesto = "/".join(parte for parte in (prefix.strip("/"), "manifest.json") if parte)
    documento = {
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "bucket": bucket,
        "region": region_real,
        "prefijo": prefix,
        "archivos": manifiesto,
    }
    s3.put_object(
        Bucket=bucket,
        Key=clave_manifiesto,
        Body=json.dumps(documento, indent=2).encode("utf-8"),
        ContentType="application/json",
        ServerSideEncryption="AES256",
    )
    print(f"[S3] Manifiesto: s3://{bucket}/{clave_manifiesto}")
    print(f"[S3] Publicacion completada: {len(manifiesto)} Parquet")


def main():
    parser = argparse.ArgumentParser(description="Publica el Data Lake local en AWS S3.")
    parser.add_argument("--bucket", default=os.getenv("S3_BUCKET", DEFAULT_BUCKET), help="Nombre global del bucket S3.")
    parser.add_argument("--prefix", default=os.getenv("S3_PREFIX", DEFAULT_PREFIX), help="Prefijo raíz dentro del bucket.")
    parser.add_argument("--region", default=os.getenv("AWS_REGION", DEFAULT_REGION), help="Región AWS, por ejemplo us-east-1.")
    parser.add_argument("--profile", default=os.getenv("AWS_PROFILE", DEFAULT_PROFILE), help="Perfil AWS opcional.")
    parser.add_argument("--no-verify", action="store_true", help="No verificar el tamaño remoto después de subir.")
    args = parser.parse_args()
    try:
        publicar_data_lake(args.bucket, args.prefix, args.region, args.profile, not args.no_verify)
    except (NoCredentialsError, BotoCoreError, ClientError, FileNotFoundError, ValueError, RuntimeError) as error:
        print(f"[S3][ERROR] {error}")
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()