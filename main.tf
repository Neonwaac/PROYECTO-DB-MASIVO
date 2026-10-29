terraform {
  required_version = ">= 1.4.0"
}

# Marcador IaC para la entrega academica.
# MongoDB Atlas se configura por separado con MONGO_URI en .env.
resource "terraform_data" "heavycult_environment" {
  input = {
    project         = "heavycult"
    data_lake_zones = "raw,processed,curated"
  }
}
