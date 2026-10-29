# 台帳の文章の訳

行 ID で引く。「元の文」は訳したときの日本語（台帳の表示文、なければ値）。日本語が変わると生成が止まるので、訳し直してから元の文を書き換える。

| ID | 元の文 | en | de | fr |
|---|---|---|---|---|
| COM-BH-DEATH | 減らない | not lost | kein Verlust | intacte |
| COM-LB-RULE | 順位で溜まる量に倍率 | Fill rate scaled by rank | Aufladung je nach Platz | Recharge selon le rang |
| COM-MATCH-DRAW | 2部隊以上が同時に目標値へ達すると引き分け | 2+ teams reach goal at once: draw | 2+ Fraktionen zugleich am Ziel: Unentschieden | 2 camps ou + au score cible ensemble : égalité |
| COM-MATCH-TIMEOUT | 時間切れは多い順 | At time limit: ranked by score | Zeitablauf: nach Punkten | Temps écoulé : classement par score |
| NAA-CLAIM-GUARDIAN | アクセス中の味方はガーディアンでかばえない | Guardian can't cover allies accessing objects | Wächter schützt keine interagierenden Verbündeten | Gardien : sans effet si l'allié interagit |
| NAA-CLAIM-INTERRUPT | 契約の実行中に攻撃を受けると中断 | Claim interrupted if attacked | Angriff während Vereinigung = Abbruch | Pacte interrompu si attaqué |
| NAA-CLAIM-LOCK | 契約した土地は、終わるまで奪われない | Claimed ovoos can't be taken until claim ends | Vereinigter Fleck bis zum Ende nicht einnehmbar | Capturée : imprenable jusqu'à la fin |
| NAA-CLAIM-LOOK | 契約した土地の柱に、部隊の紋章入りの旗が立つ | Claimed ovoo: team crest flag on its pillar | Vereinigter Fleck: Fahne mit Fraktionswappen an der Säule | Capturée : drapeau aux armoiries du camp sur le pilier |
| NAA-CLAIM-MULTI | 人数で速くならない | More players ≠ faster | mehr Spieler nicht schneller | Pas plus rapide à plusieurs |
| NAA-NOREPEAT | 同じ地点には続けて出ない | Never same spot twice in a row | Nie zweimal nacheinander am selben Ort | Jamais deux fois de suite au même endroit |
| NAA-OVOO-RECIPIENT | 契約した部隊だけに、契約の間ずっと入る | Claiming team only, for the whole claim | Nur vereinigte Fraktion, für die ganze Vereinigung | Seul le camp du pacte gagne, pendant tout le pacte |
| NAA-RANK-CENTER | マップの中心に近い地点ほど高ランクが出やすい | Higher ranks likelier near map center | Nahe Kartenmitte eher hoher Rang | Rangs élevés plus fréquents au centre |
| NAA-SPAWN-REFILL | 契約が終わると、別の地点が予告になる | When a claim ends, another spot goes Activating | Vereinigung endet → anderer Ort im Wartezustand | Fin du pacte : un autre endroit passe En préparation |
| NAA-STATE-WARN | 上空の記号が完成すると契約できる | Claimable once overhead symbol completes | Symbol oben vollständig → Vereinigung möglich | Indicateur complet : pacte possible |
| NAA-TIME-TREND | 時間が経つほど上限が減り、高ランクが出やすい | Over time: lower max, higher ranks likelier | Mit der Zeit: Max. sinkt, eher hoher Rang | Avec le temps : max en baisse, rangs élevés plus fréquents |
| NAA-WARN-NOTICE | 予告が始まると、お知らせのメッセージが出る | Message appears when Activating starts | Wartezustand beginnt → Meldung erscheint | Message au début de l'annonce |
| SEC-BH-CMDR-WHO | 着弾点にいた全員 | all at impact point | alle am Einschlag | tous au point d'impact |
| SEC-BH-DRONE-WHO | 最多ダメのパーティ全員 | all of top-damage party | ganze Top-Schaden-Gruppe | toute l'équipe aux plus gros dégâts |
| SEC-CMDR-DIST | 受け止めた部隊へ | to absorbing team | an blockende Fraktion | Au camp qui encaisse |
| SEC-CMDR-PTS-UNIT | 予兆1か所ごと | per indicator | pro Warnpunkt | Par zone d'impact |
| SEC-DRONE-DIST | 部隊に与ダメ割合で分配 | split by team dmg share | je Fraktion nach Schaden | Selon dégâts des camps |
| SEC-EVT-FIRST-KIND | システムかドローン | node or drone | Modul oder Drohne | sphère ou drone |
| SEC-EVT-HUD-NEXT | 戦況情報に次の出現の時間（と種類） | Frontline Campaign Info shows next spawn time (and type) | Schlachtinfo zeigt Zeit und Art des nächsten Erscheinens | la fenêtre de situation affiche délai et type de la suivante |
| SEC-EVT-PANEL-ONEWAY | 中央への一方通行 | one-way to center | Einbahn zur Mitte | aller simple au centre |
| SEC-EVT-PANEL-STOP | 出現の終わりまで | end | Ende | la fin |
| SEC-NODE-DIST | HP0ごとに与ダメ割合 | dmg share at each HP 0 | je LP 0 nach Schaden | Par PV 0, selon dégâts |
| SEC-SHEER-WILL | 拠点エリアの中は「不退転」で与ダメージが大幅に上がる | In key locations, Sheer Will greatly raises dmg dealt | „Fest entschlossen“ in Stellung: mehr Schaden | Poste : « Détermination », dégâts fortement accrus |
| SEI-OCC-CAPTURE-BONUS | 占拠した瞬間の加点はない（加算は占拠中だけ） | No points for occupying itself (only while held) | Kein Bonus beim Besetzen (Punkte nur solange besetzt) | Aucun bonus à la prise (gain en occupant) |
| SEI-OCC-ENEMY | 敵の占拠中は2回の占拠で奪う（1回目で中立） | Enemy-held: occupy twice (1st makes it neutral) | Feindlich besetzt: 2× besetzen (1. → neutral) | Ennemi : 2 prises (la 1re le libère) |
| SEI-OCC-INTERRUPT | 攻撃を受けると中断 | Interrupted if attacked | bei Angriff Abbruch | Interrompu si attaqué |
| SEI-OCC-LOCKOUT | 状態が変わった直後は、しばらくアクセスできない | Briefly inaccessible after status changes | Nach Zustandswechsel kurz keine Interaktion | Après changement : inaccessible un moment |
| SEI-OCC-PERSIST | 占拠したら、離れても加算は続く | Once occupied, gains continue even if you leave | Besetzt: Punkte laufen weiter, auch wenn man geht | Occupé : le gain continue même absent |
| SEI-RANK-NO-B-LATE | ランクBは出ない | No Rank B | kein Rang B | pas de rang B |
| SEI-RANK-TREND | 高ランクほど出にくい。時間が経つと高ランクが出やすい | Higher ranks rarer; likelier as time passes | Hoher Rang seltener; mit der Zeit häufiger | Rangs élevés rares, puis plus fréquents |
| SEI-TOME-NEUTRAL-DRAIN | 中立の間、残りの情報値は減らない | Remaining data doesn't drop while Unoccupied | Neutral: Rest-Daten sinken nicht | Libre : données restantes intactes |
| SEI-TOME-STACK | 複数を占拠すると、それぞれの加算の合計 | Multiple held: gains add up | Mehrere besetzt: Summe aller | Plusieurs occupés : gains cumulés |
| SHA-ICE-BH | 戦意高揚の与ダメージ上昇はアイスドトームリスにも乗る | Battle High dmg bonus also applies to icebound tomeliths | Euphorie-Schadensbonus wirkt auch auf Vereiste Echolithen | Bonus d'Ivresse du combat valable sur les mémolithes |
| SHA-ICE-DISTRIB | 壊した時点で、各部隊の与ダメージの割合で分ける | On destruction, split by each team's dmg share | Beim Zersplittern nach Schadensanteil der Fraktionen verteilt | À la destruction : partage selon les dégâts de chaque camp |
| SHA-MAP-STATES | 表示なし（破壊直後）→ 黒い影（停止中）→ 縁取り・光る影（予告）→ 氷のアイコン（攻撃できる） | None (just destroyed) → black shadow (inactive) → outline/glowing shadow (warning) → ice icon (attackable) | Nichts (frisch zersplittert) → Schwarzer Schatten (Ruhezustand) → Umrandung, leuchtender Schatten (Warnung) → Eis-Symbol (angreifbar) | Rien (détruit) → Ombre noire (désactivé) → Contour / ombre lumineuse (annonce) → Glace (attaquable) |
| SHA-S-REACT-RULE | 1個ごとに1か所ずつ | 1 spot per 1 destroyed | pro Stück 1 Ort | un lieu par petit détruit |
| TRI-AURORA-HIGHRANK | 高ランクが出やすい | Higher ranks likelier | eher hoher Rang | rangs élevés plus fréquents |
| TRI-AURORA-LB-STACK | 順位の倍率・英雄のファンタジアと重なる | Stacks with rank rate & Final Fantasia | stapelt mit Platz-Faktor & Fantasie des Helden | Cumul : classement, Fantaisie héroïque |
| TRI-AURORA-NO-B | ランクBは出ない | No Rank B | kein Rang B | pas de rang B |
| TRI-CIRCLE-CONTEST | 敵がいる間は進まない | No progress while enemies inside | Feind drin: stoppt | Ennemi dedans : bloqué |
| TRI-CIRCLE-DEFEND | 味方がいる間は取られない | Can't be taken while allies inside | Verbündete drin: sicher | allié dedans : protégé |
| TRI-CIRCLE-HEADCOUNT | 人数で速くならない | More players ≠ faster | mehr Spieler nicht schneller | Pas plus rapide à plusieurs |
| TRI-CIRCLE-KEEP | 確定したサークルは離れてよい | Secured fields can be left | Gesicherter Zirkel darf verlassen werden | Cercle acquis : on peut le quitter |
| TRI-CIRCLE-OVERWRITE | 制圧までは他部隊のサークルも塗り替えられる | Until claimed, other teams' fields can be retaken | Bis zur Besetzung fremde Zirkel umfärbbar | Cercles adverses reprenables avant contrôle |
| TRI-CIRCLE-RESET | 確定する前に無人になると最初から | Emptied before secured: progress resets | Leer vor Sicherung → von vorn | Vidé avant acquisition : retour à zéro |
| TRI-CLAIM-CONDITION | 戦略サークルを全部同じ部隊で占拠すると制圧 | Claimed when one team secures all fields of triumph | Alle Zirkel einer Fraktion → besetzt | Tous les cercles au même camp : Contrôlé |
| TRI-CLAIM-LOCK | 制圧した目標地は奪われない | Claimed triumphs can't be taken | Besetzter Triumphpunkt nicht einnehmbar | Point contrôlé : imprenable |
| TRI-OBJ-RECIPIENT | 制圧した部隊だけに、制圧の間ずっと入る | Claiming team only, for the whole claim | Nur besetzende Fraktion, solange besetzt | Seul le camp qui contrôle gagne, tant que le point est Contrôlé |
| TRI-SNOW-BLESS-TIMING | 円が満ちたとき中にいると付く | Granted if inside when circle fills | Wer drin ist, wenn der Kreis voll ist | si dedans, cercle plein |
| TRI-SNOW-STATUE-CENTER | 中央の三叉路が雪像でふさがる | Snow soldiers block central fork | Schneestatuen blockieren mittlere Gabelung | Un bonhomme de neige bloque le carrefour central |
| TRI-TIMEOUT | 時間切れは多い順 | At time limit: ranked by score | Zeitablauf: nach Punkten | Temps écoulé : classement par score |
