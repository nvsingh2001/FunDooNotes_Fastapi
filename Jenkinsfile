pipeline {
    agent any

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''
                cd /home/ubuntu/FunDooNotes_Fastapi
                source .venv/bin/activate
                pip install -r requirements.txt
                '''
            }
        }

        stage('Run Tests') {
            steps {
                sh '''
                cd /home/ubuntu/FunDooNotes_Fastapi
                source .venv/bin/activate
                pytest
                '''
            }
        }

        stage('Deploy') {
            steps {
                sh '''
                cd /home/ubuntu/FunDooNotes_Fastapi
                git pull origin main
                source .venv/bin/activate
                pip install -r requirements.txt
                sudo systemctl restart fastapi
                '''
            }
        }
    }
}
