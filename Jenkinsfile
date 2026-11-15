// Declarative pipeline: build once, test, scan, then promote the SAME image
// dev -> test -> staging -> (approval) -> prod, with automatic rollback.
pipeline {
  agent any

  options {
    timeout(time: 60, unit: 'MINUTES')
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '20'))
    timestamps()
  }

  parameters {
    string(name: 'REGISTRY', defaultValue: '',
           description: 'Optional registry path, e.g. docker.io/youruser . Empty = keep images local only')
    booleanParam(name: 'SCAN_STRICT', defaultValue: false,
                 description: 'Fail the build on HIGH/CRITICAL vulnerabilities (otherwise only report)')
    booleanParam(name: 'DEPLOY_PROD', defaultValue: true,
                 description: 'Offer the production deployment (still needs a manual approval)')
  }

  environment {
    DOCKER_BUILDKIT = '1'
    SMOKE_HOST      = 'host.docker.internal'   // how this Jenkins container reaches the published ports
    SCAN_STRICT     = "${params.SCAN_STRICT}"
  }

  stages {

    stage('Prepare') {
      steps {
        script {
          env.TAG = sh(script: 'git rev-parse --short=8 HEAD', returnStdout: true).trim()
          env.REGISTRY = params.REGISTRY?.trim() ? params.REGISTRY.trim() : 'shop'
          def branch = env.BRANCH_NAME ?: env.GIT_BRANCH ?: ''
          env.IS_MAIN = (branch == 'main' || branch == 'origin/main') ? 'true' : 'false'
          currentBuild.displayName = "#${env.BUILD_NUMBER} ${env.TAG}"
          echo "Image tag: ${env.TAG}  |  registry: ${env.REGISTRY}  |  main branch: ${env.IS_MAIN}"
        }
      }
    }

    stage('Validate') {
      parallel {
        stage('Compose files') {
          steps {
            sh '''#!/bin/bash -e
              for e in dev test staging prod; do
                TAG=check docker compose --env-file env/$e.env -f docker-compose.yml config -q
                echo "compose config ok: $e"
              done
            '''
          }
        }
        stage('Shell syntax') {
          steps {
            sh '''#!/bin/bash -e
              for f in scripts/*.sh api/entrypoint.sh; do bash -n "$f"; echo "syntax ok: $f"; done
            '''
          }
        }
      }
    }

    stage('Unit tests') {
      steps { sh 'bash scripts/test.sh' }
    }

    stage('Build images') {
      steps { sh 'bash scripts/build.sh "$TAG"' }
    }

    stage('Vulnerability scan') {
      steps {
        sh '''#!/bin/bash
          set -o pipefail
          mkdir -p reports
          bash scripts/scan.sh 2>&1 | tee reports/trivy.txt
        '''
      }
    }

    stage('Push to registry') {
      when { expression { return params.REGISTRY?.trim() } }
      steps {
        withCredentials([usernamePassword(credentialsId: 'registry-creds',
                                          usernameVariable: 'REG_USER',
                                          passwordVariable: 'REG_PASS')]) {
          sh '''#!/bin/bash -e
            echo "$REG_PASS" | docker login "${REGISTRY%%/*}" -u "$REG_USER" --password-stdin
            docker push "$REGISTRY/shop-api:$TAG"
            docker push "$REGISTRY/shop-web:$TAG"
            docker logout "${REGISTRY%%/*}"
          '''
        }
      }
    }

    stage('Deploy DEV') {
      steps { sh 'bash scripts/deploy.sh dev "$TAG"' }
    }

    stage('Integration tests (DEV)') {
      steps { sh 'bash scripts/integration.sh "$(bash scripts/url.sh dev)"' }
    }

    stage('Deploy TEST') {
      when { expression { env.IS_MAIN == 'true' } }
      steps { sh 'bash scripts/deploy.sh test "$TAG"' }
    }

    stage('Integration tests (TEST)') {
      when { expression { env.IS_MAIN == 'true' } }
      steps { sh 'bash scripts/integration.sh "$(bash scripts/url.sh test)"' }
    }

    stage('Deploy STAGING') {
      when { expression { env.IS_MAIN == 'true' } }
      steps { sh 'bash scripts/deploy.sh staging "$TAG"' }
    }

    stage('Approval for PRODUCTION') {
      when { expression { env.IS_MAIN == 'true' && params.DEPLOY_PROD } }
      steps {
        // In a company this is where the change ticket / change board approval is checked.
        timeout(time: 1, unit: 'HOURS') {
          input message: "Deploy ${env.TAG} to PRODUCTION?", ok: 'Deploy'
        }
      }
    }

    stage('Deploy PROD') {
      when { expression { env.IS_MAIN == 'true' && params.DEPLOY_PROD } }
      steps { sh 'bash scripts/deploy.sh prod "$TAG"' }
    }
  }

  post {
    success { echo "Pipeline succeeded for ${env.TAG}" }
    failure { echo "Pipeline FAILED for ${env.TAG}: read the console output of the failed stage" }
    always  { archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true }
  }
}
