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

        /*
        * =====================================================
        * Run automated unit tests and generate
        * coverage and JUnit reports.
        *
        * This stage is executed before deployment to ensure
        * only tested code is deployed.
        * =====================================================
        */
        stage('Run Tests & Generate Coverage') {
            steps {
                sh '''
                mkdir -p artifacts

                python3 -m pip install -r requirements.txt

                bash -lc 'set -o pipefail;
                python3 -m pytest \
                    --cov=. \
                    --cov-report=term \
                    --cov-report=xml:artifacts/coverage.xml \
                    --cov-report=html:artifacts/htmlcov \
                    --junitxml=artifacts/pytest-report.xml \
                    2>&1 | tee artifacts/pytest.log'
                '''

                echo 'Unit tests completed successfully. Coverage and JUnit reports have been generated.'
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
                    ansible/deploy_docker_playbook.yaml \
                    2>&1 | tee artifacts/production_ansible_deploy.log'
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

                } catch (diagnosticsError) {

                    echo "AI diagnostics warning: ${diagnosticsError}"

                }
            }
        }

        always {

            junit(
                allowEmptyResults: true,
                testResults: 'artifacts/pytest-report.xml'
            )

            archiveArtifacts(
                artifacts: 'artifacts/coverage.xml,artifacts/htmlcov/**,artifacts/pytest-report.xml,artifacts/pytest.log,artifacts/ai-diagnostics/*.md',
                allowEmptyArchive: true
            )

            sh '''
            rm -f "$WORKSPACE/.env"
            '''
        }
    }
}