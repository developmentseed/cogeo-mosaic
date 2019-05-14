# Variables
variable "region" {
  type    = "string"
  default = "us-east-1"
}

variable "stage_name" {
  description = "The stage name(production/staging/etc..)"
  default     = "production"
}

# API Gateway + Lambda
module "cogeo_mosaic_api" {
  source = "github.com/developmentseed/tf-lambda-proxy-apigw"

  # General options
  project    = "cogeo-mosaic"
  stage_name = "${var.stage_name}"
  region     = "${var.region}"

  # Lambda options
  lambda_name    = "api"
  lambda_runtime = "python3.6"
  lambda_memory  = 3008
  lambda_timeout = 10
  lambda_package = "package.zip"                   # local file created by `docker-compose run --rm package`
  lambda_handler = "cogeo_mosaic.handlers.api.APP"

  lambda_env = {
    PYTHONWARNINGS                     = "ignore"
    GDAL_DATA                          = "/var/task/share/gdal"
    GDAL_CACHEMAX                      = "512"
    VSI_CACHE                          = "TRUE"
    VSI_CACHE_SIZE                     = "536870912"
    CPL_TMPDIR                         = "/tmp"
    GDAL_HTTP_MERGE_CONSECUTIVE_RANGES = "YES"
    GDAL_HTTP_MULTIPLEX                = "YES"
    GDAL_HTTP_VERSION                  = "2"
    MAX_THREADS                        = "10"
    GDAL_DISABLE_READDIR_ON_OPEN       = "EMPTY_DIR"
    CPL_VSIL_CURL_ALLOWED_EXTENSIONS   = ".tif"
  }
}

# Outputs
output "endpoint" {
  description = "COGEO-mosaic endpoint url"
  value       = "${module.cogeo_mosaic_api.api_url}"
}
