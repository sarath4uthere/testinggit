pipeline {
  agent any

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Build image') {
      steps {
        sh 'docker build -t flask-notes:${BUILD_NUMBER} .'
      }
    }

    stage('Test image') {
      steps {
        sh '''docker run --rm flask-notes:${BUILD_NUMBER} python -c "import flask, psycopg2; print('imports ok')"'''
      }
    }

    stage('Tag latest') {
      steps {
        sh 'docker tag flask-notes:${BUILD_NUMBER} flask-notes:latest'
      }
    }
	    stage('Push to Docker Hub') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'dockerhub-creds',
                                          usernameVariable: 'DH_USER',
                                          passwordVariable: 'DH_PASS')]) {
          sh '''
            echo "$DH_PASS" | docker login -u "$DH_USER" --password-stdin
            docker tag flask-notes:${BUILD_NUMBER} $DH_USER/flask-notes:${BUILD_NUMBER}
            docker push $DH_USER/flask-notes:${BUILD_NUMBER}
            docker logout
          '''
        }
      }
    }
  }

  post {
    success { echo "Build ${BUILD_NUMBER} succeeded" }
    failure { echo "Build ${BUILD_NUMBER} failed" }
  }
}