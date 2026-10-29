import argparse
import os
from pathlib import Path

import boto3
import pandas as pd
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")
DEFAULT_BUCKET = "abp-data-lake-neonwaac-2026"
DEFAULT_REGION = "us-east-1"
DEFAULT_PROFILE = "heavycult"


def leer_parquet_s3(bucket, key, region=None, profile=None, destino=None):
    session = boto3.Session(profile_name=profile, region_name=region)
    s3 = session.client("s3")
    nombre_local = Path(destino) if destino else BASE_DIR / ".s3_cache" / Path(key).name
    nombre_local.parent.mkdir(parents=True, exist_ok=True)
    s3.download_file(bucket, key, str(nombre_local))
    dataframe = pd.read_parquet(nombre_local)
    print(f"[S3] s3://{bucket}/{key}")
    print(f"[S3] Archivo local temporal: {nombre_local}")
    print(f"[S3] Filas: {len(dataframe):,} | Columnas: {len(dataframe.columns)}")
    print(f"[S3] Columnas: {list(dataframe.columns)}")
    print(dataframe.head(5).to_string(index=False))
    return dataframe


def main():
    parser = argparse.ArgumentParser(description="Lee un Parquet publicado en S3.")
    parser.add_argument("--bucket", default=os.getenv("S3_BUCKET", DEFAULT_BUCKET), required=False)
    parser.add_argument("--key", default=os.getenv("S3_KEY", "heavycult/processed/ventas_procesadas.parquet"))
    parser.add_argument("--region", default=os.getenv("AWS_REGION", DEFAULT_REGION))
    parser.add_argument("--profile", default=os.getenv("AWS_PROFILE", DEFAULT_PROFILE))
    parser.add_argument("--destino", help="Ruta local opcional para la descarga temporal.")
    args = parser.parse_args()
    if not args.bucket:
        parser.error("Indica --bucket o configura S3_BUCKET en .env.")
    try:
        leer_parquet_s3(args.bucket, args.key, args.region, args.profile, args.destino)
    except (NoCredentialsError, BotoCoreError, ClientError, OSError) as error:
        print(f"[S3][ERROR] {error}")
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
