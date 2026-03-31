pipeline {
    agent any

    environment {
        IMAGE_NAME = 'evo-ai'
        CONTAINER_NAME = 'evo-ai-container'
    }

    stages {

        stage('Clone Repository') {
            steps {
                git 'https://github.com/VEDANTPANDEY35/Evo-AI.git'
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    sh 'docker build -t $IMAGE_NAME .'
                }
            }
        }

        stage('Stop Old Container') {
            steps {
                script {
                    sh 'docker stop $CONTAINER_NAME || true'
                    sh 'docker rm $CONTAINER_NAME || true'
                }
            }
        }

        stage('Run Container') {
            steps {
                script {
                    sh '''
                    docker run -d \
                    --name $CONTAINER_NAME \
                    $IMAGE_NAME
                    '''
                }
            }
        }
    }
}
