pipeline {
    agent any

    stages {
        stage('Checkout Source Code') {
            steps {
                checkout scm
            }
        }

        stage('Deploy to Production') {
            steps {
                sh '''
                docker exec -u root jenkins_server bash -c "
                cd /var/jenkins_home/workspace/RPMarketplace-Production &&
                ansible-playbook -i ansible/hosts ansible/deploy_docker_playbook.yaml
                "
                '''
            }
        }

        stage('Confirm Production URL') {
            steps {
                echo 'Production is available at: http://localhost:5000'
            }
        }
    }

    post {
        success {
            echo 'Production deployment completed successfully.'
        }

        failure {
            echo 'Production deployment failed.'
        }
    }
}