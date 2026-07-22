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

        stage('Clean Diagnostic Artifacts') {
            steps {
                sh '''
                rm -rf "$WORKSPACE/artifacts"
                mkdir -p "$WORKSPACE/artifacts/ai-diagnostics"
                '''
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

        stage('Install Dependencies') {
            steps {
                sh '''
                python3 -m venv venv
                . venv/bin/activate
                pip install -r requirements.txt
                '''
            }
        }

        stage('Run Tests') {
            steps {
                sh '''
                mkdir -p artifacts/ai-diagnostics
                . venv/bin/activate
                bash -lc 'set -o pipefail; PYTHONPATH="$WORKSPACE" python3 -m pytest tests/ 2>&1 | tee artifacts/production_pytest.log'
                '''
            }
        }

        stage('Validate Ansible') {
            steps {
                sh '''
                mkdir -p artifacts/ai-diagnostics
                bash -lc 'set -o pipefail; ansible-playbook \
                    -i ansible/hosts \
                    ansible/deploy_docker_playbook.yaml \
                    --syntax-check 2>&1 | tee artifacts/production_ansible_validate.log'
                '''
            }
        }

        stage('Deploy to Production with Ansible') {
            steps {
                sh '''
                mkdir -p artifacts/ai-diagnostics
                bash -lc 'set -o pipefail; ansible-playbook \
                    -i ansible/hosts \
                    ansible/deploy_docker_playbook.yaml 2>&1 | tee artifacts/production_ansible_deploy.log'
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
            script {
                try {
                    sh '''
                    mkdir -p artifacts/ai-diagnostics
                    if ls artifacts/*.log >/dev/null 2>&1; then
                        rm -f artifacts/production_jenkins_failure.log
                        for log_file in artifacts/*.log; do
                            if [ -f "$log_file" ] && [ "$log_file" != "artifacts/production_jenkins_failure.log" ]; then
                                cat "$log_file"
                            fi
                        done > artifacts/production_jenkins_failure.log

                        python3 -m devops.ai_agent.analyse_failure \
                            --source jenkins \
                            --input-file artifacts/production_jenkins_failure.log \
                            --output-file artifacts/ai-diagnostics/production_jenkins_report.md || true

                        for log_file in artifacts/production_ansible_*.log; do
                            if [ -f "$log_file" ]; then
                                report_name="$(basename "$log_file" .log)_report.md"
                                python3 -m devops.ai_agent.analyse_failure \
                                    --source ansible \
                                    --input-file "$log_file" \
                                    --output-file "artifacts/ai-diagnostics/$report_name" || true
                            fi
                        done
                    fi
                    '''
                    archiveArtifacts artifacts: 'artifacts/ai-diagnostics/*.md', allowEmptyArchive: true
                } catch (diagnosticsError) {
                    echo "AI diagnostics warning: ${diagnosticsError}"
                }
            }
        }

        always {
            sh '''
            rm -f "$WORKSPACE/.env"
            '''
        }
    }
}
