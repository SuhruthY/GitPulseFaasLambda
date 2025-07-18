# GitPulseFaasLambda

Real-time GitHub events monitoring using AWS Lambda and EventBridge.

## 🌟 Features

- Real-time monitoring of GitHub public events
- AWS Lambda serverless architecture
- EventBridge scheduled triggers
- Support for multiple GitHub event types:
  - Push events
  - Issue events
  - Watch events
  - Fork events
  - Pull Request events
  - Create events

## 🚀 Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/GitPulseFaasLambda.git
cd GitPulseFaasLambda
```

2. Create a `.env` file with your credentials:
```env
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=your_region
GITHUB_TOKEN=your_github_token
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## 📦 Deployment

Deploy to AWS Lambda:
```bash
python src/utils/deploy.py
```

Clean up resources:
```bash
python src/utils/delete.py
```

## 🏃 Local Testing

Run locally with:
```bash
LOCAL_TEST=1 python src/main.py
```

## 🔄 Event Types Monitored

- `PushEvent`: Code pushes
- `IssuesEvent`: Issue creation/updates
- `WatchEvent`: Repository stars
- `ForkEvent`: Repository forks
- `PullRequestEvent`: PR activities
- `CreateEvent`: New branch/tag creation

## ⚙️ Configuration

- Default region: us-east-1
- Lambda memory: 512MB
- Timeout: 300 seconds
- EventBridge trigger: Every 2 minutes

## 🛟 Troubleshooting

1. **Lambda not running**: Check CloudWatch logs
2. **Permission issues**: Verify IAM role permissions
3. **Rate limiting**: Check GitHub API rate limits
4. **Missing logs**: Ensure correct timezone (IST) setup

## 📝 License

MIT License - feel free to use and modify as needed.
