#!/bin/bash

export AWS_PAGER="" # To avoid less

# What we need to define

IMAGE_NAME="citibike-lambda"
AWS_REGION="us-east-1"

LAMBDA_ROLE_NAME='lambda-basic-execution-role'

function_name='citibike-docker'



AWS_ACCOUNT_ID=$(aws sts get-caller-identity | jq -r ".Account")

# Get latest commit SHA and current datetime
COMMIT_SHA=$(git rev-parse --short HEAD)
DATETIME=$(date +"%Y%m%d-%H%M%S")
IMAGE_TAG="${COMMIT_SHA}-${DATETIME}"

ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
IMAGE_URI="${ECR_URI}/${IMAGE_NAME}:${IMAGE_TAG}"


# Create repo if not exists
aws ecr describe-repositories --repository-names ${IMAGE_NAME} --region ${AWS_REGION} > /dev/null 2>&1 || \
aws ecr create-repository --repository-name ${IMAGE_NAME} --region ${AWS_REGION}


aws ecr get-login-password \
    --region ${AWS_REGION} \
    | docker login \
    --username AWS \
    --password-stdin ${ECR_URI}


# Build with lamdda-builder on arm64
BUILDER_NAME="lambda-builder"

echo "Checking for buildx builder: ${BUILDER_NAME}"

# If there is no lambda-builder, create it
if ! docker buildx ls | grep -q -w "${BUILDER_NAME}"; then
    echo "Builder '${BUILDER_NAME}' not found. Creating..."
    docker buildx create --name ${BUILDER_NAME} --driver docker-container --use
else
    echo "Builder '${BUILDER_NAME}' already exists. Setting as active builder..."
    docker buildx use ${BUILDER_NAME}
fi

echo "Bootstrapping builder '${BUILDER_NAME}'..."
docker buildx inspect ${BUILDER_NAME} --bootstrap
echo "Builder is ready."


docker buildx build \
    -f Dockerfile.lambda \
    --builder lambda-builder \
    --platform linux/amd64 \
    --load \
    -t ${IMAGE_NAME}:${IMAGE_TAG} .

docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_URI}
docker push ${IMAGE_URI} 


aws ecr batch-get-image \
    --repository-name ${IMAGE_NAME} \
    --image-ids imageTag=${IMAGE_TAG} \
    --region ${AWS_REGION} \
    --query 'images[].imageManifestMediaType' \
    --output text


# Update or create lambda function
if aws lambda get-function --function-name "${function_name}" --region ${AWS_REGION} >/dev/null 2>&1; then
    echo "Updating existing Lambda function..."
    aws lambda update-function-code \
    --function-name "${function_name}" \
    --image-uri "${IMAGE_URI}" \
    --region ${AWS_REGION}
else
    echo "Creating new Lambda function..."
    aws lambda create-function \
    --function-name "${function_name}" \
    --package-type Image \
    --code ImageUri="${IMAGE_URI}" \
    --role arn:aws:iam::${AWS_ACCOUNT_ID}:role/${LAMBDA_ROLE_NAME} \
    --region ${AWS_REGION}
fi

# Wait until code update is done
echo "Waiting for Lambda update to complete..."
aws lambda wait function-updated --function-name "${function_name}" --region ${AWS_REGION}


# Update configuration (timeout, memory, env, etc.)
# timeout default: 3
# memory default: 128
echo "Updating Lambda configuration..."
aws lambda update-function-configuration \
    --function-name "${function_name}" \
    --timeout 60 \
    --memory-size 128 \
    --ephemeral-storage '{"size": 512}' \
    --region ${AWS_REGION}

echo "✅ Deployment complete!"