pipeline {
    agent any

    environment {
        IMAGE_NAME = "fundoonotes"
        IMAGE_TAG = "latest"
        CONTAINER_NAME = "fundoonotes"
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build Docker Image') {
            steps {
                sh '''
                docker build --pull -t ${IMAGE_NAME}:${IMAGE_TAG} .
                '''
            }
        }

        stage('Stop Existing Container') {
            steps {
                sh '''
                docker stop ${CONTAINER_NAME} || true
                docker rm ${CONTAINER_NAME} || true
                '''
            }
        }

        stage('Run Container') {
            steps {
                sh '''
                docker run -d \
                  --name ${CONTAINER_NAME} \
                  --restart unless-stopped \
                  -p 8000:8000 \
                  ${IMAGE_NAME}:${IMAGE_TAG}
                '''
            }
        }
    }
}
