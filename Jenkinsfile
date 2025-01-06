pipeline {
    agent {
        label 'builder'
    }

    options {
        timestamps()
    }

    environment {
        BRANCH_NAME = 'fast-embed-server'
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
                    sh "cp -Rf ${env.MODEL_DIR}/fast-bge-small-zh-v1.5 ./models"
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
                    docker stop fast-embed-server||true
                    docker rm fast-embed-server||true
                    docker run -itd --name fast-embed-server --restart always \
                        --network lite \
                        -e APP_NAME=fast-embed-server \
                        -e APP_PORT=80 \
                        etherfurnace/fast-embed-server
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