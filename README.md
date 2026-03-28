# 2003000_alfa
# aggiorna
git checkout dev
git pull origin dev

# nuovo lavoro
git checkout -b feature/x

# lavori...
git add .
git commit -m "feat: ..."

# push
git push origin feature/x

# PR su dev

# aggiorni branch
git checkout dev
git pull
git checkout feature/x
git merge dev
