
Update chmod permissons for .sh scripts
* So ur scripts are callable as soon they are cloned and you dont need to run chmod +x on them

Instructions:
git update-index --chmod=+x your-script.sh
git add your-script.sh
git commit -m "Make script executable"
git push


in case some arent run this command from scripts/
find . -name "*.sh" -exec chmod +x {} +
echo "Scripts are now executable!"