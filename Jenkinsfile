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

        stage('Test Docker') {
            steps {
                sh 'docker --version'
            }
        }

        stage('Build Docker images') {
            steps {
                sh 'docker-compose build'
            }
        }

        stage('Run Containers') {
            steps {
                sh 'docker-compose up -d'
            }
        }

        stage('Push Docker image') {
            steps {
                sh '''
                    echo "$CREDS_PSW" | docker login -u "$CREDS_USR" --password-stdin
                    docker push $DOCKER_IMAGE
                '''
            }
        }

        stage('Cleanup') {
            steps {
                sh 'docker-compose down'
            }
        }
    }
}
