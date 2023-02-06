sudo pip3 install -r requirements.txt
sudo cp agents_covid.conf /etc/supervisor/conf.d/
sudo cp agents_covid_nginx.conf /etc/nginx/sites-enabled/
sudo supervisorctl update
sudo systemctl restart nginx
sudo certbot --nginx -d covid.ai.medsenger.ru
