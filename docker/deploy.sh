#!/bin/bash

# Outlook邮件管理系统 Docker部署脚本
# 使用方法: ./deploy.sh [build|start|stop|restart|logs|status]

set -e

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
BACKEND_DIR="$PROJECT_ROOT/backend"
DATA_DIR="$PROJECT_ROOT/data"

PROJECT_NAME="outlook-mail-automation"
IMAGE_NAME="outlook-mail-system"
CONTAINER_NAME="outlook-mail-automation"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Docker是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
}

# 检查配置文件
check_config() {
    CONFIG_FILE="$BACKEND_DIR/configs/config.txt"
    if [ ! -f "$CONFIG_FILE" ]; then
        log_warning "configs/config.txt 不存在，创建空文件"
        mkdir -p "$(dirname "$CONFIG_FILE")"
        cat <<'EOF' > "$CONFIG_FILE"
# 批量邮箱账户配置文件
# 格式：邮箱----密码----refresh_token----client_id
EOF
        log_info "请编辑 $CONFIG_FILE 添加邮箱配置"
    fi

    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        log_error "未找到根目录下的 .env，请先根据 .env.example 创建"
        exit 1
    fi

    mkdir -p "$DATA_DIR"
}

# 构建镜像
build_image() {
    log_info "开始构建Docker镜像..."
    (cd "$SCRIPT_DIR" && docker-compose build --no-cache)
    log_success "Docker镜像构建完成"
}

# 启动服务
start_service() {
    log_info "启动Outlook邮件管理系统..."
    check_config
    (cd "$SCRIPT_DIR" && docker-compose up -d)
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 5
    
    # 检查服务状态
    if (cd "$SCRIPT_DIR" && docker-compose ps | grep -q "Up"); then
        log_success "服务启动成功！"
        log_info "访问地址: http://localhost:5001"
        log_info "管理界面: http://localhost:5001/admin"
        log_info "查看日志: docker-compose logs -f"
    else
        log_error "服务启动失败，请查看日志"
        (cd "$SCRIPT_DIR" && docker-compose logs)
        exit 1
    fi
}

# 停止服务
stop_service() {
    log_info "停止Outlook邮件管理系统..."
    (cd "$SCRIPT_DIR" && docker-compose down)
    log_success "服务已停止"
}

# 重启服务
restart_service() {
    log_info "重启Outlook邮件管理系统..."
    (cd "$SCRIPT_DIR" && docker-compose restart)
    log_success "服务已重启"
}

# 查看日志
show_logs() {
    log_info "显示服务日志..."
    (cd "$SCRIPT_DIR" && docker-compose logs -f)
}

# 查看状态
show_status() {
    log_info "服务状态:"
    (cd "$SCRIPT_DIR" && docker-compose ps)
    
    echo ""
    log_info "容器资源使用:"
    if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "$CONTAINER_NAME"; then
        docker stats --no-stream "$CONTAINER_NAME"
    else
        log_warning "容器未运行"
    fi
}

# 清理资源
cleanup() {
    log_info "清理Docker资源..."
    docker-compose down -v
    docker system prune -f
    log_success "清理完成"
}

# 更新系统
update_system() {
    log_info "更新系统..."
    stop_service
    build_image
    start_service
    log_success "系统更新完成"
}

# 显示帮助信息
show_help() {
    echo "Outlook邮件管理系统 Docker部署脚本"
    echo ""
    echo "使用方法: $0 [命令]"
    echo ""
    echo "可用命令:"
    echo "  build     构建Docker镜像"
    echo "  start     启动服务"
    echo "  stop      停止服务"
    echo "  restart   重启服务"
    echo "  logs      查看日志"
    echo "  status    查看状态"
    echo "  cleanup   清理资源"
    echo "  update    更新系统"
    echo "  help      显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 build       # 构建镜像"
    echo "  $0 start       # 启动服务"
    echo "  $0 logs        # 查看日志"
}

# 主函数
main() {
    check_docker
    
    case "${1:-help}" in
        "build")
            build_image
            ;;
        "start")
            start_service
            ;;
        "stop")
            stop_service
            ;;
        "restart")
            restart_service
            ;;
        "logs")
            show_logs
            ;;
        "status")
            show_status
            ;;
        "cleanup")
            cleanup
            ;;
        "update")
            update_system
            ;;
        "help"|*)
            show_help
            ;;
    esac
}

# 执行主函数
main "$@"
