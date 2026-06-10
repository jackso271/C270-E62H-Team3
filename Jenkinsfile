pipeline {
    agent any

    stages {
        stage('Install Dependencies') {
            steps {
                script {
                    if (isUnix()) {
                        sh 'python -m pip install --upgrade pip'
                        sh 'pip install -r requirements.txt'
                    } else {
                        bat 'python -m pip install --upgrade pip'
                        bat 'pip install -r requirements.txt'
                    }
                }
            }
        }

        stage('Run Tests') {
            steps {
                script {
                    if (isUnix()) {
                        sh 'python -m pytest'
                    } else {
                        bat 'python -m pytest'
                    }
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    if (isUnix()) {
                        sh 'docker build -t c270-e62h-team3 .'
                    } else {
                        bat 'docker build -t c270-e62h-team3 .'
                    }
                }
            }
        }
    }
}
