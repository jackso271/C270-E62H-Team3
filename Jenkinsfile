pipeline {
    agent any

    options {
        skipDefaultCheckout(true)
    }

    stages {
        stage('Checkout Source Code') {
            steps {
                checkout scm
            }
        }

        stage('Prepare Production Environment') {
            steps {
                withCredentials([
                    file(
                        credentialsId: 'rpmarketplace-production-env',
                        variable: 'PRODUCTION_ENV_FILE'
                    )
                ]) {
                    sh '''
                    cp "$PRODUCTION_ENV_FILE" "$WORKSPACE/.env"
                    chmod 600 "$WORKSPACE/.env"
                    test -s "$WORKSPACE/.env"
                    '''
                }
            }
        }

        stage('Validate Ansible') {
            steps {
                sh '''
                ansible-playbook \
                    -i ansible/hosts \
                    ansible/deploy_docker_playbook.yaml \
                    --syntax-check
                '''
            }
        }

        stage('Deploy to Production with Ansible') {
            steps {
                sh '''
                ansible-playbook \
                    -i ansible/hosts \
                    ansible/deploy_docker_playbook.yaml
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

        always {
            sh '''
            rm -f "$WORKSPACE/.env"
            '''
        }
    }
}
