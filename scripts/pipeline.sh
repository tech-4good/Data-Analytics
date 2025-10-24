#!/bin/bash
set -e

echo "Pipeline Tech 4 Good"

# Lambda 1
echo ""
echo "Executando: RAW -> TRUSTED"
aws lambda invoke \
  --function-name LambdaT4G \
  --payload '{}' \
  response1.json > /dev/null

if grep -q '"statusCode": 200' response1.json; then
    echo "Lambda 1 Concluída!"
else 
    echo "Erro na lambda1"
    cat response1.json
    exit 1
fi 
