pipeline {
    agent any

    stages {

        stage('Checkout Source Code') {
            steps {
                checkout scm
            }
        }

        stage('Build Staging Docker Image') {
            steps {
                sh 'docker build -t rp-marketplace-staging .'
            }
        }

        stage('Verify Staging Docker Image') {
            steps {
                sh 'docker images | grep rp-marketplace-staging'
            }
        }

        stage('Deploy to Staging with Ansible') {
            steps {
                sh 'ansible-playbook -i ansible/hosts ansible/deploy_docker_playbook.yaml'
            }
        }

        stage('Verify Staging Container') {
            steps {
                sh 'docker ps --format "table {{.Names}}\\t{{.Ports}}" | grep rpmarketplace-staging'
            }
        }
    }

    post {
        success {
            echo 'Staging pipeline completed successfully.'
        }

        failure {
            echo 'Staging pipeline failed.'
        }
    }
}