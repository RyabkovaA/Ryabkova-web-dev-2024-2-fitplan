pipeline {
    agent any

    environment {
        DOCKER_IMAGE = 'fawnyler00/devops_app:latest'
        CREDS = credentials('dockerhub-creds')
    }

    stages {
        stage('Checkout') {
            steps {
                git 'https://github.com/RyabkovaA/Ryabkova-web-dev-2024-2-fitplan.git'
            }
        }

        stage('Build Docker image') {
            steps {
                sh 'docker build -t $DOCKER_IMAGE .'
            }
        }

        stage('Push to Docker Hub') {
            steps {
                sh '''
                    echo "$CREDS_PSW" | docker login -u "$CREDS_USR" --password-stdin
                    docker push $DOCKER_IMAGE
                '''
            }
        }
    }
}
