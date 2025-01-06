pipeline {
    agent {
        label 'builder'
    }

    options {
        timestamps()
    }

    environment {
        BRANCH_NAME = 'bce-embed-server'
        IMAGE_NAME = "etherfurnace/${BRANCH_NAME}"
        IMAGE_TAG='latest'
    }

    stages {
        stage('构建前通知'){
           steps {
                sh """
                    curl '${env.NOTIFICATION_URL}' \
                    -H 'Content-Type: application/json' \
                    -d '{
                        "msgtype": "text",
                        "text": {
                            "content": "[${BRANCH_NAME}]: 🚀 开始构建"
                        }
                    }'
                """
           }
        }

        stage('克隆代码仓库') {
            steps {
                git url: 'https://github.com/WeOps-Lab/roche-limit', branch: BRANCH_NAME
            }
       }

       stage('构建镜像') {
            steps {
                script {
                    sh "rm -Rf ./apps/example/"
                    sh "mkdir -p models"
                    sh "cp -Rf ${env.MODEL_DIR}/bce-embedding-base_v1 ./models"
                    sh "cp -Rf ${env.MODEL_DIR}/bce-reranker-base_v1 ./models"
                    sh "sudo docker build -f ./support-files/docker/Dockerfile -t ${IMAGE_NAME}:${IMAGE_TAG} ."
                }
            }
       }

       stage('推送镜像'){
            steps {
                script {
                    sh "sudo docker push  ${IMAGE_NAME}:${IMAGE_TAG}"
                }
            }
       }

        stage('更新环境'){
            agent { 
                label 'docker' 
            }
            options {
                skipDefaultCheckout true
            }
            steps {
                script {
                    sh """
                    docker pull ${IMAGE_NAME}:${IMAGE_TAG}
                    docker stop bce-embed-server || true
                    docker rm bce-embed-server || true
                    docker run -itd --name bce-embed-server --restart always \
                        --network lite \
                        -e APP_NAME=bce-embed-server \
                        -e APP_PORT=80 \
                        etherfurnace/bce-embed-server
                    """
                }
            }
       }
    }

    post {
        success {
            sh """
                curl '${env.NOTIFICATION_URL}' \
                -H 'Content-Type: application/json' \
                -d '{
                    "msgtype": "text",
                    "text": {
                        "content": "[${BRANCH_NAME}]: 🎉 构建成功"
                    }
                }'
            """
        }
        failure {
            sh """
                curl '${env.NOTIFICATION_URL}' \
                -H 'Content-Type: application/json' \
                -d '{
                    "msgtype": "text",
                    "text": {
                        "content": "[${BRANCH_NAME}]: ❌ 构建失败"
                    }
                }'
            """
        }
    }
}