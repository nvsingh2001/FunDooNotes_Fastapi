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
                python3 -m venv .venv
                . .venv/bin/activate
                pip install -r requirements.txt
                '''
            }
        }
        stage('Deploy') {
            steps {
                sh '''
                rsync -av --delete \
                    --exclude='.git' \
                    --exclude='.venv' \
                    ./ /home/ubuntu/FunDooNotes_Fastapi
                '''
            }
        }

        stage('Install Production Dependencies') {
            steps {
                sh '''
                cd /home/ubuntu/FunDooNotes_Fastapi
                . .venv/bin/activate

                pip install -r requirements.txt
                '''
            }
        }

        stage('Restart Service') {
            steps {
                sh '''
                sudo systemctl restart fundoonotes
                '''
            }
        }
    }
}
