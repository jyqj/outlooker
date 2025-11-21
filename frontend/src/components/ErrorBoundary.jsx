import React from 'react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error('捕获到未处理的前端异常', error, info);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
    if (typeof this.props.onReset === 'function') {
      this.props.onReset();
    }
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex flex-col items-center justify-center gap-4 bg-muted/50 px-4 text-center">
          <h1 className="text-2xl font-semibold text-foreground">页面加载失败</h1>
          <p className="text-sm text-muted-foreground">
            {this.state.error?.message || '出现未知错误，请重试或联系管理员。'}
          </p>
          <button
            type="button"
            onClick={this.handleRetry}
            className="px-4 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition"
          >
            重新加载
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
