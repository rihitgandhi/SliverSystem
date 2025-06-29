# 🚀 Production Deployment Guide

This guide will help you deploy the SliverSystem accessibility analysis tool to production.

## 📋 Prerequisites

- Google Gemini API key
- GitHub account
- Render.com account (or similar platform)
- Domain name (optional)

## 🔧 Step 1: Prepare Your Repository

1. **Ensure all files are committed:**
   ```bash
   git add .
   git commit -m "Prepare for production deployment"
   git push origin main
   ```

2. **Verify your `.env` file is in `.gitignore`** (security)

## 🌐 Step 2: Deploy to Render.com

### Option A: Automatic Deployment (Recommended)

1. **Connect to Render:**
   - Go to [render.com](https://render.com)
   - Sign up/Login with your GitHub account
   - Click "New +" → "Web Service"

2. **Connect Repository:**
   - Select your GitHub repository
   - Render will automatically detect it's a Python app

3. **Configure Service:**
   - **Name:** `sliver-system-backend`
   - **Environment:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`

4. **Set Environment Variables:**
   - `GEMINI_API_KEY`: Your Google Gemini API key
   - `FLASK_SECRET_KEY`: Generate a secure random key
   - `FLASK_DEBUG`: `false`
   - `HOST`: `0.0.0.0`
   - `PORT`: `10000`

5. **Deploy:**
   - Click "Create Web Service"
   - Render will automatically build and deploy

### Option B: Using render.yaml (Advanced)

1. **Update `render.yaml`** with your specific settings
2. **Push to GitHub** - Render will auto-deploy

## 🔒 Step 3: Security Configuration

### Environment Variables
```bash
# Required
GEMINI_API_KEY=your_gemini_api_key_here
FLASK_SECRET_KEY=your_secure_secret_key_here

# Optional
FLASK_DEBUG=false
LOG_LEVEL=INFO
ENABLE_METRICS=true
```

### Generate Secure Secret Key
```python
import secrets
print(secrets.token_hex(32))
```

## 🌍 Step 4: Domain Configuration (Optional)

1. **Add Custom Domain:**
   - In Render dashboard, go to your service
   - Click "Settings" → "Custom Domains"
   - Add your domain

2. **SSL Certificate:**
   - Render provides free SSL certificates
   - Automatically configured for custom domains

## 📊 Step 5: Monitoring & Health Checks

### Health Check Endpoint
Your app includes a health check at `/api/health`

### Monitoring Setup
1. **Enable Logs:** View logs in Render dashboard
2. **Set up Alerts:** Configure email/SMS alerts
3. **Performance Monitoring:** Use Render's built-in metrics

## 🔧 Step 6: Frontend Deployment

### Option A: GitHub Pages (Static Files)
1. **Create a new repository** for frontend
2. **Copy static files** (HTML, CSS, JS)
3. **Enable GitHub Pages** in repository settings
4. **Update API URLs** to point to your backend

### Option B: Netlify/Vercel
1. **Connect repository** to Netlify/Vercel
2. **Configure build settings**
3. **Set environment variables**

## 🧪 Step 7: Testing Production

1. **Test Health Endpoint:**
   ```bash
   curl https://your-app.onrender.com/api/health
   ```

2. **Test Accessibility Analysis:**
   - Visit your deployed app
   - Test with a real website URL
   - Verify all features work

3. **Performance Testing:**
   - Test with various website sizes
   - Monitor response times
   - Check error handling

## 🔄 Step 8: Continuous Deployment

### Automatic Deployments
- Render automatically deploys on `git push`
- Set up branch protection rules in GitHub
- Use feature branches for development

### Manual Deployments
```bash
# Trigger manual deployment
git commit --allow-empty -m "Trigger deployment"
git push origin main
```

## 🚨 Troubleshooting

### Common Issues

1. **Build Failures:**
   - Check `requirements.txt` for correct versions
   - Verify Python version compatibility
   - Check build logs in Render dashboard

2. **Runtime Errors:**
   - Check application logs
   - Verify environment variables
   - Test locally with production config

3. **API Key Issues:**
   - Ensure `GEMINI_API_KEY` is set correctly
   - Check API key permissions
   - Verify API quota limits

### Debug Commands
```bash
# Check logs
curl https://your-app.onrender.com/api/health

# Test API endpoint
curl -X POST https://your-app.onrender.com/api/score \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

## 📈 Step 9: Scaling & Performance

### Auto-scaling
- Render automatically scales based on traffic
- Configure min/max instances in `render.yaml`

### Performance Optimization
- Use CDN for static assets
- Implement caching strategies
- Monitor API response times

## 🔐 Security Best Practices

1. **Environment Variables:**
   - Never commit secrets to Git
   - Use secure secret management
   - Rotate keys regularly

2. **API Security:**
   - Implement rate limiting
   - Add request validation
   - Use HTTPS only

3. **Monitoring:**
   - Set up error tracking (Sentry)
   - Monitor for suspicious activity
   - Regular security audits

## 📞 Support

If you encounter issues:
1. Check Render documentation
2. Review application logs
3. Test locally with production config
4. Contact support with specific error messages

---

**🎉 Congratulations!** Your SliverSystem is now deployed and ready to help make the web more accessible! 