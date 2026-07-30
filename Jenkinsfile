/*
 * =====================================================
 * CI Build Notification Helper
 * Displays a build summary at the end of the pipeline.
 * =====================================================
 */
def printBuildNotification(String status) {

    echo """
====================================================
RP Marketplace CI Build Notification
====================================================

Project      : ${env.JOB_NAME}
Build Number : ${env.BUILD_NUMBER}
Branch       : ${env.BRANCH_NAME ?: 'main'}
Status       : ${status}
Build URL    : ${env.BUILD_URL}

Reports
✔ JUnit Report
✔ Coverage Report
✔ HTML Coverage
✔ AI Diagnostics (if generated)

====================================================
"""
}

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

        /*
        * =====================================================
        * Run automated unit tests and generate
        * coverage and JUnit reports before production deploy.
        * =====================================================
        */

        stage('Run Tests & Generate Coverage') {
            steps {
                sh '''
                mkdir -p artifacts
                : > artifacts/production_test.log

                bash -lc 'set -e -o pipefail;
                CI_VENV="$WORKSPACE/.venv-ci";
                rm -rf "$CI_VENV";
                python3 -m venv "$CI_VENV" 2>&1 | tee -a artifacts/production_test.log;
                "$CI_VENV/bin/python" -m pip install --upgrade pip 2>&1 | tee -a artifacts/production_test.log;
                "$CI_VENV/bin/python" -m pip install -r requirements.txt 2>&1 | tee -a artifacts/production_test.log;

                "$CI_VENV/bin/python" -m pytest \
                    --cov=. \
                    --cov-report=term \
                    --cov-report=xml:artifacts/coverage.xml \
                    --cov-report=html:artifacts/htmlcov \
                    --junitxml=artifacts/junit.xml \
                    2>&1 | tee -a artifacts/production_test.log'
                '''

                echo 'Unit tests completed successfully. Coverage and JUnit reports have been generated.'
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

        stage('Validate ZAP Ansible Playbook') {
            steps {
                sh '''
                mkdir -p artifacts/ai-diagnostics

                bash -lc 'set -o pipefail; ansible-playbook \
                    -i ansible/hosts \
                    ansible/deploy_docker_zap_playbook.yaml \
                    --syntax-check \
                    2>&1 | tee artifacts/zap_ansible_validate.log'
                '''
            }
        }

        stage('Deploy ZAP Test Environment') {
            steps {
                sh '''
                mkdir -p artifacts/ai-diagnostics

            bash -lc 'set -o pipefail; ansible-playbook \
                -i ansible/hosts \
                ansible/deploy_docker_zap_playbook.yaml \
                2>&1 | tee artifacts/zap_ansible_deploy.log'
            '''
            }
        }
        
        stage('OWASP ZAP Security Scan') {
            steps {
                sh '''
                    set -e -o pipefail

                    echo "Starting OWASP ZAP baseline scan"
                    
                    mkdir -p artifacts/zap
                    chmod 777 artifacts/zap

                    cleanup(){
                        docker rm -f zap-scanner 2>/dev/null || true
                        docker volume rm zap-work 2>/dev/null || true
                    }
                    
                    trap cleanup EXIT

                    cleanup
                    docker volume create zap-work

                    docker run \
                        --name zap-scanner \
                        --user root \
                        --network rpmarketplace-network \
                        -v zap-work:/zap/wrk \
                        ghcr.io/zaproxy/zaproxy:stable \
                        zap-baseline.py \
                        -t http://rpmarketplace-zap:5000 \
                        -r zap-report.html \
                        -I \
                        --autooff \
                        -T 10 \
                        -z "-silent" \
                        2>&1 | tee artifacts/zap/zap_scan.log
                    
                    docker cp zap-scanner:/zap/wrk/zap-report.html \
                        artifacts/zap/zap-report.html
                    
                    test -s artifacts/zap/zap-report.html

                    docker rm -f zap-scanner
                    docker volume rm zap-work

                    echo "OWASP ZAP scan and report generation completed."
                '''
            }
        }

        stage('Confirm ZAP Test URL') {
            steps {
                echo 'ZAP test environment is available at: http://localhost:5005'
            }
        }
    }

    post {
        always {
            junit(
                allowEmptyResults: true,
                testResults: 'artifacts/junit.xml'
            )

            archiveArtifacts(
                artifacts: 'artifacts/coverage.xml,artifacts/htmlcov/**,artifacts/junit.xml,artifacts/*.log,artifacts/ai-diagnostics/*.md,artifacts/zap/zap-report.html,artifacts/zap/zap_scan.log',
                allowEmptyArchive: true
            )

            sh '''
            rm -f "$WORKSPACE/.env"
            '''
        }

        success {
            echo 'Production deployment completed successfully.'

            printBuildNotification("SUCCESS")
        }

        failure {
            echo 'Production deployment failed.'
            script {
                try {
                    sh '''
                    mkdir -p artifacts/ai-diagnostics
                    AI_PYTHON="$WORKSPACE/.venv-ci/bin/python"
                    if [ ! -x "$AI_PYTHON" ]; then
                        AI_PYTHON=python3
                    fi

                    rm -f artifacts/production_jenkins_failure.log artifacts/production_jenkins_failure.raw.log

                    if ls artifacts/*.log >/dev/null 2>&1; then
                        for log_file in artifacts/*.log; do
                            if [ -f "$log_file" ] && [ "$log_file" != "artifacts/production_jenkins_failure.log" ] && [ "$log_file" != "artifacts/production_jenkins_failure.raw.log" ]; then
                                cat "$log_file"
                            fi
                        done > artifacts/production_jenkins_failure.raw.log
                    else
                        {
                            echo "No captured stage log exists."
                            echo "Job: ${JOB_NAME:-unknown}"
                            echo "Build number: ${BUILD_NUMBER:-unknown}"
                            echo "Build URL: ${BUILD_URL:-unknown}"
                        } > artifacts/production_jenkins_failure.raw.log
                    fi

                    PYTHONPATH="$WORKSPACE" "$AI_PYTHON" -c 'from devops.ai_agent.redact_sensitive_data import write_redacted_file; write_redacted_file("artifacts/production_jenkins_failure.raw.log", "artifacts/production_jenkins_failure.log")' || printf '%s\n' 'Sanitized diagnostic log unavailable because redaction failed. Raw log was not archived.' > artifacts/production_jenkins_failure.log
                    rm -f artifacts/production_jenkins_failure.raw.log

                    PYTHONPATH="$WORKSPACE" "$AI_PYTHON" -m devops.ai_agent.analyse_failure \
                        --source jenkins \
                        --input-file artifacts/production_jenkins_failure.log \
                        --output-file artifacts/ai-diagnostics/production_jenkins_report.md || true

                    for log_file in artifacts/production_ansible_*.log; do
                        if [ -f "$log_file" ]; then
                            report_name="$(basename "$log_file" .log)_report.md"
                            PYTHONPATH="$WORKSPACE" "$AI_PYTHON" -m devops.ai_agent.analyse_failure \
                                --source ansible \
                                --input-file "$log_file" \
                                --output-file "artifacts/ai-diagnostics/$report_name" || true
                        fi
                    done

                    # OWASP ZAP Ansible diagnostics
                    for log_file in artifacts/zap_ansible_*.log; do
                        if [ -f "$log_file" ]; then
                            report_name="$(basename "$log_file" .log)_report.md"
                            PYTHONPATH="$WORKSPACE" "$AI_PYTHON" -m devops.ai_agent.analyse_failure \
                                --source ansible \
                                --input-file "$log_file" \
                                --output-file "artifacts/ai-diagnostics/$report_name" || true
                        fi
                    done
                    '''
                    archiveArtifacts artifacts: 'artifacts/ai-diagnostics/*.md', allowEmptyArchive: true
                } catch (diagnosticsError) {
                    echo "AI diagnostics warning: ${diagnosticsError}"
                }
            }
        }
    }
}
