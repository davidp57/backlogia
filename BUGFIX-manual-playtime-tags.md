# Fix: Manual Playtime Tags Persistence for Multi-Store Games

## Problème
Les tags de playtime manuels ne persistaient pas correctement pour les jeux possédés sur plusieurs stores (ex: Xbox ET Steam). Le tag revenait à l'ancien après changement même si le toast confirmait le succès.

## Cause racine
Deux problèmes identifiés :

1. **Incohérence game_id vs primary_game** : Quand un jeu existe sur plusieurs stores (même IGDB ID), la page game_detail sélectionne un `primary_game` (celui avec le plus de données), mais récupérait le tag du jeu original de l'URL au lieu du primary_game.

2. **Auto-tagging écrasant les tags manuels** : La fonction `update_auto_labels_for_game()` ne vérifiait pas si un tag manuel existait avant d'appliquer les tags automatiques.

3. **UI non mise à jour** : Le rechargement de page ne fonctionnait pas toujours, et le dropdown ne mettait pas à jour le checkmark.

## Corrections apportées

### 1. `web/services/system_labels.py` (lignes 96-110)
Ajout d'une vérification pour respecter les tags manuels existants :

```python
# Check if there's already a manual tag (auto=0) for this game
# If yes, respect it and don't auto-tag
cursor.execute("""
    SELECT COUNT(*) FROM game_labels
    WHERE game_id = ? AND auto = 0
    AND label_id IN (
        SELECT id FROM labels WHERE system = 1 AND type = 'system_tag'
    )
""", (game_id,))
manual_tag_count = cursor.fetchone()[0]

if manual_tag_count > 0:
    # User has manually set a tag, don't override it
    return
```

**Emplacement** : Dans la fonction `update_auto_labels_for_game()`, juste après le commentaire `"""Update auto-generated system labels for a single game based on playtime."""` et la récupération du jeu.

### 2. `web/routes/library.py` (ligne ~226)
Changement de `game_id` à `primary_game["id"]` pour récupérer le bon tag :

**AVANT** :
```python
# Get current system labels (playtime tags) for this game
cursor.execute("""
    SELECT l.name
    FROM labels l
    JOIN game_labels gl ON l.id = gl.label_id
    WHERE gl.game_id = ? AND l.system = 1 AND l.type = 'system_tag'
""", (game_id,))
```

**APRÈS** :
```python
# Get current system labels (playtime tags) for the PRIMARY game (the one we'll display)
cursor.execute("""
    SELECT l.name
    FROM labels l
    JOIN game_labels gl ON l.id = gl.label_id
    WHERE gl.game_id = ? AND l.system = 1 AND l.type = 'system_tag'
""", (primary_game["id"],))
```

### 3. `web/templates/game_detail.html`

#### A. Ajout de l'ID au bouton (lignes ~1577-1592)
Ajouter `id="playtime-pill"` aux deux versions du bouton :

**AVANT** :
```html
<button class="tag-pill playtime-set" onclick="togglePlaytimeMenu(event)">
```

**APRÈS** :
```html
<button id="playtime-pill" class="tag-pill playtime-set" onclick="togglePlaytimeMenu(event)">
```

Et aussi pour la version "unset" :
```html
<button id="playtime-pill" class="tag-pill unset" onclick="togglePlaytimeMenu(event)">
```

#### B. Mise à jour de la fonction setPlaytimeTag() (lignes ~2927-2945)
Remplacer toute la fonction `setPlaytimeTag()` :

**AVANT** :
```javascript
async function setPlaytimeTag(tag) {
    try {
        const response = await fetch(`/api/game/${gameId}/manual-playtime-tag`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({label_name: tag})
        });

        if (response.ok) {
            const text = tag ? `Playtime tag set to "${tag}"` : 'Playtime tag removed';
            showToast(text, 'success');
            document.getElementById('playtime-dropdown').style.display = 'none';
            setTimeout(() => window.location.reload(), 1000);
        } else {
            showToast('Failed to set playtime tag', 'error');
        }
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    }
}
```

**APRÈS** :
```javascript
async function setPlaytimeTag(tag) {
    try {
        const response = await fetch(`/api/game/${gameId}/manual-playtime-tag`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({label_name: tag})
        });

        if (response.ok) {
            const text = tag ? `Playtime tag set to "${tag}"` : 'Playtime tag removed';
            showToast(text, 'success');
            document.getElementById('playtime-dropdown').style.display = 'none';
            
            // Update the pill UI immediately without page reload
            const playtimePill = document.getElementById('playtime-pill');
            if (tag) {
                const iconMap = {
                    'Never Launched': '🎮',
                    'Just Tried': '👀',
                    'Played': '🎯',
                    'Well Played': '⭐',
                    'Heavily Played': '🏆'
                };
                const icon = iconMap[tag] || '🎮';
                playtimePill.className = 'tag-pill playtime-set';
                playtimePill.innerHTML = `${icon} ${tag} <span class="arrow">&#9662;</span>`;
            } else {
                playtimePill.className = 'tag-pill unset';
                playtimePill.innerHTML = '🎮 Playtime <span class="arrow">&#9662;</span>';
            }
            
            // Update the dropdown menu to show the correct selected item
            const dropdown = document.getElementById('playtime-dropdown');
            const items = dropdown.querySelectorAll('.dropdown-item');
            items.forEach(item => {
                // Remove 'current' class from all items
                item.classList.remove('current');
                // Extract the tag from onclick attribute (e.g., "setPlaytimeTag('Played')")
                const onclick = item.getAttribute('onclick');
                if (onclick) {
                    const match = onclick.match(/setPlaytimeTag\('([^']+)'\)/);
                    if (match) {
                        const itemTag = match[1];
                        // Add 'current' class only if it matches exactly
                        if (itemTag === tag) {
                            item.classList.add('current');
                        }
                    }
                }
            });
        } else {
            showToast('Failed to set playtime tag', 'error');
        }
    } catch (error) {
        showToast('Error: ' + error.message, 'error');
    }
}
```

## Test de validation
1. Trouver un jeu possédé sur plusieurs stores (même IGDB ID)
2. Sur la page de détail, changer le tag de playtime
3. Vérifier que :
   - Le tag change immédiatement dans l'UI
   - Le menu dropdown affiche le checkmark sur le bon tag
   - Après rechargement de page, le tag est toujours correct
   - Le tag manuel persiste même après une sync Steam

## Fichiers modifiés
- `web/services/system_labels.py`
- `web/routes/library.py`
- `web/templates/game_detail.html`

## Notes complémentaires
- Aucun changement de schéma de base de données requis
- Le nettoyage des doublons de tags a été fait avec le script `cleanup_tags.py` (59 doublons supprimés)
- La colonne `auto` dans `game_labels` distingue les tags manuels (0) des automatiques (1)
