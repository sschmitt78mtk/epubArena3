document.addEventListener('DOMContentLoaded', function() {
  const table = document.getElementById('translationstable');

  function toggleColumn(colIndex, show) {
      const rows = table.getElementsByTagName('tr');
      for (let i = 0; i < rows.length; i++) {
          const cells = rows[i].getElementsByTagName('td');
          if (cells[colIndex] && cells[colIndex].classList.contains('translation')) {
              cells[colIndex].classList.toggle('hidden', !show);
          }
      }
      adjustColumnWidth(); // Breite der Spalten anpassen
      if (colIndex == 99) {
        if (show) { // Alle Zeilen der Tabelle verarbeiten
          document.querySelectorAll('tr').forEach(compareTextinRow);
        } else {
          removeHighlighting()
        }
      }
  }

  function adjustColumnWidth() {
      // const visibleColumns = table.querySelectorAll('td.translation:not(.hidden)').length; // Anzahl sichtbarer Spalten
      const visibleColumns = document.querySelectorAll('.controls input[type="checkbox"]:checked').length;
      // const newWidth = `calc(100% / ${visibleColumns})`; // Neue Breite berechnen
      newWidth = `${100 / visibleColumns}vw`; // Neue Breite berechnen
      console.log(`${visibleColumns} visibleColumns, width: ${newWidth}`)
      document.documentElement.style.setProperty('--translation-width', newWidth); // CSS-Variable aktualisieren
  }

  adjustColumnWidth(); // initial nach Laden der Seite Spaltenbreite festlegen


  function stringToColor(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
  
    // Begrenze die RGB-Werte auf einen Bereich, der helle Farben erzeugt (z. B. 200–255)
    const minBrightness = 150; // Mindesthelligkeit
    const maxBrightness = 230; // Maximale Helligkeit
  
    const r = (hash & 0xFF) % (maxBrightness - minBrightness) + minBrightness;
    const g = ((hash >> 8) & 0xFF) % (maxBrightness - minBrightness) + minBrightness;
    const b = ((hash >> 16) & 0xFF) % (maxBrightness - minBrightness) + minBrightness;
  
    // Konvertiere die RGB-Werte in einen Hex-Farbcode
    const toHex = (value) => {
      const hex = value.toString(16);
      return hex.length === 1 ? '0' + hex : hex;
    };
  
    return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
  }

// Funktion zur Suche des längsten gemeinsamen Teilstrings, der an Wortgrenzen beginnt und endet
function longestCommonSubstringAtWordBoundaries(s1, s2) {
  const words1 = s1.split(/\b/);
  const words2 = s2.split(/\b/);
  let longestLength = 0;
  let longestMatch = '';

  for (let i = 0; i < words1.length; i++) {
    for (let j = 0; j < words2.length; j++) {
      let k = 0;
      while (i + k < words1.length && j + k < words2.length && words1[i + k] === words2[j + k]) {
        k++;
      }
      if (k > 0) {
        const match = words1.slice(i, i + k).join('');
        if (match.length >= 25 && match.length > longestLength) {
          longestLength = match.length;
          longestMatch = match;
        }
      }
    }
  }

  return longestMatch;
}

// Rekursive Funktion zum Hervorheben der Texte
function highlightCommon(text1, text2) {
  const lcs = longestCommonSubstringAtWordBoundaries(text1, text2);
  if (!lcs) return { parts1: [text1], parts2: [text2] };

  const index1 = text1.indexOf(lcs);
  const index2 = text2.indexOf(lcs);

  if (index1 === -1 || index2 === -1) return { parts1: [text1], parts2: [text2] };

  const before = highlightCommon(
    text1.substring(0, index1),
    text2.substring(0, index2)
  );
  const after = highlightCommon(
    text1.substring(index1 + lcs.length),
    text2.substring(index2 + lcs.length)
  );

  const span1 = document.createElement('span');
  span1.style.backgroundColor = stringToColor(lcs);
  span1.textContent = lcs;

  const span2 = document.createElement('span');
  span2.style.backgroundColor = span1.style.backgroundColor;
  span2.textContent = lcs;

  return {
    parts1: [...before.parts1, span1, ...after.parts1],
    parts2: [...before.parts2, span2, ...after.parts2]
  };
}

// Verarbeitung jeder Tabellenzeile
function compareTextinRow(row) {
  const cells = row.querySelectorAll('td:not(.hidden)');
  if (cells.length < 2) return;

  const result = highlightCommon(cells[0].textContent, cells[1].textContent);

  cells[0].innerHTML = '';
  cells[1].innerHTML = '';

  result.parts1.forEach(part => cells[0].appendChild(
    typeof part === 'string' ? document.createTextNode(part) : part
  ));
  result.parts2.forEach(part => cells[1].appendChild(
    typeof part === 'string' ? document.createTextNode(part) : part
  ));
}
function removeHighlighting() {
  const rows = document.querySelectorAll('tr');
  rows.forEach(row => {
    const cells = row.querySelectorAll('td.translation');
    cells.forEach(cell => {
      // Erstelle einen DocumentFragment, um den bereinigten Inhalt zu speichern
      const fragment = document.createDocumentFragment();
      
      // Durchlaufe alle Kindknoten der Zelle
      Array.from(cell.childNodes).forEach(child => {
        if (child.nodeType === Node.ELEMENT_NODE && child.tagName === 'SPAN') {
          // Wenn das Kind ein <span>-Element ist, füge seinen Textinhalt zum Fragment hinzu
          fragment.appendChild(document.createTextNode(child.textContent));
        } else {
          // Andernfalls füge den Knoten direkt zum Fragment hinzu
          fragment.appendChild(child.cloneNode(true));
        }
      });

      // Ersetze den Inhalt der Zelle durch das bereinigte Fragment
      cell.innerHTML = ''; // Leere die Zelle
      cell.appendChild(fragment); // Füge den bereinigten Inhalt hinzu
    });
  });
}
    // es folgen Codegenerierte Toggle-Functions und
    // });