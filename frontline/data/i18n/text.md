# 台帳の文章の訳

行 ID で引く。「元の文」は訳したときの日本語（台帳の表示文、なければ値）。日本語が変わると生成が止まるので、訳し直してから元の文を書き換える。

| ID | 元の文 | en | de | fr | ko | zh-hans | zh-hant |
|---|---|---|---|---|---|---|---|
| COM-BH-DEATH | 減らない | not lost | kein Verlust | intacte | 줄지 않음 | 不会减少 | 不會減少 |
| COM-LB-RULE | 順位で溜まる量に倍率 | Fill rate scaled by rank | Aufladung je nach Platz | Recharge selon le rang | 순위에 따라 축적량에 배율 | 积蓄量按排位乘以倍率 | 蓄積量依排位乘以倍率 |
| COM-MATCH-DRAW | 2部隊以上が同時に目標値へ達すると引き分け | 2+ teams reach goal at once: draw | 2+ Fraktionen zugleich am Ziel: Unentschieden | 2 camps ou + au score cible ensemble : égalité | 2개 부대 이상이 동시에 목표 점수에 도달하면 무승부 | 2支部队以上同时达到目标值则为平局 | 2支部隊以上同時達到目標值則平局 |
| COM-MATCH-TIMEOUT | 時間切れは多い順 | At time limit: ranked by score | Zeitablauf: nach Punkten | Temps écoulé : classement par score | 시간 종료 시 점수 많은 순 | 时间结束时按数值高低排位 | 時間結束時按分數高低排位 |
| NAA-CLAIM-GUARDIAN | アクセス中の味方はガーディアンでかばえない | Guardian can't cover allies accessing objects | Wächter schützt keine interagierenden Verbündeten | Gardien : sans effet si l'allié interagit | 접속 중인 아군은 수호자로 보호할 수 없음 | 正在接触场景物体的队友无法以卫护保护 | 正在接觸場景物體的隊友無法以衛護保護 |
| NAA-CLAIM-INTERRUPT | 契約の実行中に攻撃を受けると中断 | Claim interrupted if attacked | Angriff während Vereinigung = Abbruch | Pacte interrompu si attaqué | 계약 중 공격을 받으면 중단 | 契约执行中受到攻击会中断 | 契約進行中受到攻擊即中斷 |
| NAA-CLAIM-LOCK | 契約した土地は、終わるまで奪われない | Claimed ovoos can't be taken until claim ends | Vereinigter Fleck bis zum Ende nicht einnehmbar | Capturée : imprenable jusqu'à la fin | 계약한 땅은 끝날 때까지 빼앗기지 않음 | 已契约的土地在结束前不会被夺走 | 已契約的土地在契約結束前不會被奪走 |
| NAA-CLAIM-LOOK | 契約した土地の柱に、部隊の紋章入りの旗が立つ | Claimed ovoo: team crest flag on its pillar | Vereinigter Fleck: Fahne mit Fraktionswappen an der Säule | Capturée : drapeau aux armoiries du camp sur le pilier | 계약한 땅의 기둥에 부대 문장이 있는 깃발이 섬 | 已契约的土地柱上会竖起带部队纹章的旗帜 | 已契約土地的柱子上會立起帶部隊紋章的旗幟 |
| NAA-CLAIM-MULTI | 人数で速くならない | More players ≠ faster | mehr Spieler nicht schneller | Pas plus rapide à plusieurs | 인원이 많아도 빨라지지 않음 | 人数多也不会更快 | 人數多也不會更快 |
| NAA-NOREPEAT | 同じ地点には続けて出ない | Never same spot twice in a row | Nie zweimal nacheinander am selben Ort | Jamais deux fois de suite au même endroit | 같은 지점에 연속으로 나오지 않음 | 同一地点不会连续出现 | 相同地點不會連續出現 |
| NAA-OVOO-RECIPIENT | 契約した部隊だけに、契約の間ずっと入る | Claiming team only, for the whole claim | Nur vereinigte Fraktion, für die ganze Vereinigung | Seul le camp du pacte gagne, pendant tout le pacte | 계약한 부대에만, 계약 내내 계속 들어감 | 仅契约部队获得，整个契约期间持续 | 僅契約部隊獲得，契約期間持續獲得 |
| NAA-RANK-CENTER | マップの中心に近い地点ほど高ランクが出やすい | Higher ranks likelier near map center | Nahe Kartenmitte eher hoher Rang | Rangs élevés plus fréquents au centre | 맵 중앙에 가까운 지점일수록 높은 등급이 나오기 쉬움 | 越靠近地图中心的地点越容易出现高等级 | 越接近地圖中心的地點越容易出現高等級 |
| NAA-SPAWN-REFILL | 契約が終わると、別の地点が予告になる | When a claim ends, another spot goes Activating | Vereinigung endet → anderer Ort im Wartezustand | Fin du pacte : un autre endroit passe En préparation | 계약이 끝나면 다른 지점이 예고가 됨 | 契约结束后，其他地点进入预告 | 契約結束後，其他地點進入預告狀態 |
| NAA-STATE-WARN | 上空の記号が完成すると契約できる | Claimable once overhead symbol completes | Symbol oben vollständig → Vereinigung möglich | Indicateur complet : pacte possible | 상공의 기호가 완성되면 계약 가능 | 上空的记号完成后即可契约 | 上空記號完成後即可契約 |
| NAA-TIME-TREND | 時間が経つほど上限が減り、高ランクが出やすい | Over time: lower max, higher ranks likelier | Mit der Zeit: Max. sinkt, eher hoher Rang | Avec le temps : max en baisse, rangs élevés plus fréquents | 시간이 지날수록 상한이 줄고 높은 등급이 나오기 쉬움 | 时间越久上限越低，越容易出现高等级 | 隨時間經過上限減少，越容易出現高等級 |
| NAA-WARN-NOTICE | 予告が始まると、お知らせのメッセージが出る | Message appears when Activating starts | Wartezustand beginnt → Meldung erscheint | Message au début de l'annonce | 예고가 시작되면 안내 메시지가 나옴 | 预告开始时会出现通知消息 | 預告開始時會出現通知訊息 |
| SEC-BH-CMDR-WHO | 着弾点にいた全員 | all at impact point | alle am Einschlag | tous au point d'impact | 착탄 지점에 있던 전원 | 着弹点内的全体人员 | 著彈點上的所有人 |
| SEC-BH-DRONE-WHO | 最多ダメのパーティ全員 | all of top-damage party | ganze Top-Schaden-Gruppe | toute l'équipe aux plus gros dégâts | 피해량이 가장 많은 파티 전원 | 伤害最高的小队全员 | 造成傷害最多的小隊全員 |
| SEC-CMDR-DIST | 受け止めた部隊へ | to absorbing team | an blockende Fraktion | Au camp qui encaisse | 공격을 받아낸 부대에게 | 给予承接的部队 | 給予接住攻擊的部隊 |
| SEC-CMDR-PTS-UNIT | 予兆1か所ごと | per indicator | pro Warnpunkt | Par zone d'impact | 명중 지점 1곳마다 | 每个预兆点 | 每個預兆地點 |
| SEC-DRONE-DIST | 部隊に与ダメ割合で分配 | split by team dmg share | je Fraktion nach Schaden | Selon dégâts des camps | 부대별 주는 피해 비율로 분배 | 按各部队造成伤害的比例分配 | 依各部隊造成傷害的比例分配 |
| SEC-EVT-FIRST-KIND | システムかドローン | node or drone | Modul oder Drohne | sphère ou drone | 시스템 또는 요격기 | 系统或无人机 | 截擊系統或截擊無人機 |
| SEC-EVT-HUD-NEXT | 戦況情報に次の出現の時間（と種類） | Frontline Campaign Info shows next spawn time (and type) | Schlachtinfo zeigt Zeit und Art des nächsten Erscheinens | la fenêtre de situation affiche délai et type de la suivante | 전황 정보에 다음 출현 시간 (과 종류) | 战况信息显示下次出现的时间（与种类） | 戰況資訊會顯示下次出現時間（與種類） |
| SEC-EVT-PANEL-ONEWAY | 中央への一方通行 | one-way to center | Einbahn zur Mitte | aller simple au centre | 중앙으로의 일방통행 | 单向通往中央 | 往中央的單向通行 |
| SEC-EVT-PANEL-STOP | 出現の終わりまで | end | Ende | la fin | 출현 종료까지 | 至出现结束为止 | 至出現結束為止 |
| SEC-NODE-DIST | HP0ごとに与ダメ割合 | dmg share at each HP 0 | je LP 0 nach Schaden | Par PV 0, selon dégâts | HP 0마다 주는 피해 비율 | 每次HP0按造成伤害比例 | 每次HP0依造成傷害比例 |
| SEC-SHEER-WILL | 拠点エリアの中は「不退転」で与ダメージが大幅に上がる | In key locations, Sheer Will greatly raises dmg dealt | „Fest entschlossen“ in Stellung: mehr Schaden | Poste : « Détermination », dégâts fortement accrus | 거점 지역 안에서는 '불퇴전'으로 주는 피해가 크게 증가 | 据点区域内处于「坚定不移」时造成的伤害大幅提升 | 在據點區域內會因「堅定不移」使給予傷害大幅提升 |
| SEI-OCC-CAPTURE-BONUS | 占拠した瞬間の加点はない（加算は占拠中だけ） | No points for occupying itself (only while held) | Kein Bonus beim Besetzen (Punkte nur solange besetzt) | Aucun bonus à la prise (gain en occupant) | 점령한 순간의 가산은 없음 (가산은 점령 중에만) | 占领瞬间没有加分（仅在占领中累加） | 佔領瞬間不會加分（僅佔領期間持續加算） |
| SEI-OCC-ENEMY | 敵の占拠中は2回の占拠で奪う（1回目で中立） | Enemy-held: occupy twice (1st makes it neutral) | Feindlich besetzt: 2× besetzen (1. → neutral) | Ennemi : 2 prises (la 1re le libère) | 적이 점령 중이면 2회 점령으로 빼앗음 (1회차에 중립) | 敌方占领中需占领2次才能夺取（第1次变为中立） | 敵方佔領中需佔領2次才能奪取（第1次變為中立） |
| SEI-OCC-INTERRUPT | 攻撃を受けると中断 | Interrupted if attacked | bei Angriff Abbruch | Interrompu si attaqué | 공격을 받으면 중단 | 受到攻击会中断 | 受到攻擊即中斷 |
| SEI-OCC-LOCKOUT | 状態が変わった直後は、しばらくアクセスできない | Briefly inaccessible after status changes | Nach Zustandswechsel kurz keine Interaktion | Après changement : inaccessible un moment | 상태가 바뀐 직후에는 잠시 접속할 수 없음 | 状态变化后短时间内无法接触 | 狀態剛改變後，暫時無法接觸 |
| SEI-OCC-PERSIST | 占拠したら、離れても加算は続く | Once occupied, gains continue even if you leave | Besetzt: Punkte laufen weiter, auch wenn man geht | Occupé : le gain continue même absent | 점령하면 떠나도 가산은 계속됨 | 占领后即使离开也会继续累加 | 佔領後即使離開仍會持續加算 |
| SEI-RANK-NO-B-LATE | ランクBは出ない | No Rank B | kein Rang B | pas de rang B | B급은 나오지 않음 | 不会出现等级B | 不會出現等級B |
| SEI-RANK-TREND | 高ランクほど出にくい。時間が経つと高ランクが出やすい | Higher ranks rarer; likelier as time passes | Hoher Rang seltener; mit der Zeit häufiger | Rangs élevés rares, puis plus fréquents | 높은 등급일수록 나오기 어려움. 시간이 지나면 높은 등급이 나오기 쉬움 | 等级越高越难出现。时间越久越容易出现高等级 | 等級越高越不易出現。隨時間經過越容易出現高等級 |
| SEI-TOME-NEUTRAL-DRAIN | 中立の間、残りの情報値は減らない | Remaining data doesn't drop while Unoccupied | Neutral: Rest-Daten sinken nicht | Libre : données restantes intactes | 중립인 동안 남은 정보 점수는 줄지 않음 | 中立期间剩余情报值不会减少 | 中立期間，剩餘情報值不會減少 |
| SEI-TOME-STACK | 複数を占拠すると、それぞれの加算の合計 | Multiple held: gains add up | Mehrere besetzt: Summe aller | Plusieurs occupés : gains cumulés | 여러 개를 점령하면 각각의 가산 합계 | 占领多个时，各项累加合计 | 佔領多個時，為各自加算的合計 |
| SHA-ICE-BH | 戦意高揚の与ダメージ上昇はアイスドトームリスにも乗る | Battle High dmg bonus also applies to icebound tomeliths | Euphorie-Schadensbonus wirkt auch auf Vereiste Echolithen | Bonus d'Ivresse du combat valable sur les mémolithes | 투쟁심 상승의 주는 피해 증가는 얼음탑에도 적용됨 | 斗志昂扬的伤害提升也适用于冰封的石文 | 鬥志昂揚的給予傷害提升對冰封的石文也有效 |
| SHA-ICE-DISTRIB | 壊した時点で、各部隊の与ダメージの割合で分ける | On destruction, split by each team's dmg share | Beim Zersplittern nach Schadensanteil der Fraktionen verteilt | À la destruction : partage selon les dégâts de chaque camp | 파괴 시점에 각 부대의 주는 피해 비율로 나눔 | 破坏时按各部队造成伤害的比例分配 | 破壞時依各部隊造成傷害的比例分配 |
| SHA-MAP-STATES | 表示なし（破壊直後）→ 黒い影（停止中）→ 縁取り・光る影（予告）→ 氷のアイコン（攻撃できる） | None (just destroyed) → black shadow (inactive) → outline/glowing shadow (warning) → ice icon (attackable) | Nichts (frisch zersplittert) → Schwarzer Schatten (Ruhezustand) → Umrandung, leuchtender Schatten (Warnung) → Eis-Symbol (angreifbar) | Rien (détruit) → Ombre noire (désactivé) → Contour / ombre lumineuse (annonce) → Glace (attaquable) | 표시 없음 (파괴 직후) → 검은 그림자 (정지 중) → 테두리·빛나는 그림자 (예고) → 얼음 아이콘 (공격 가능) | 无显示（刚破坏）→ 黑影（停止中）→ 描边·发光影（预告）→ 冰图标（可攻击） | 無顯示（破壞後）→ 黑色影子（停止中）→ 外框·發光的影子（預告）→ 冰的圖示（可攻擊） |
| SHA-S-REACT-RULE | 1個ごとに1か所ずつ | 1 spot per 1 destroyed | pro Stück 1 Ort | un lieu par petit détruit | 1개당 1곳씩 | 每1个新增1处 | 每1個對應1處 |
| TRI-AURORA-HIGHRANK | 高ランクが出やすい | Higher ranks likelier | eher hoher Rang | rangs élevés plus fréquents | 높은 등급이 나오기 쉬움 | 容易出现高等级 | 容易出現高等級 |
| TRI-AURORA-LB-STACK | 順位の倍率・英雄のファンタジアと重なる | Stacks with rank rate & Final Fantasia | stapelt mit Platz-Faktor & Fantasie des Helden | Cumul : classement, Fantaisie héroïque | 순위 배율·영웅의 환상곡과 중첩됨 | 与排位倍率、英雄的幻想曲叠加 | 與排位倍率·英雄的幻想曲疊加 |
| TRI-AURORA-NO-B | ランクBは出ない | No Rank B | kein Rang B | pas de rang B | B급은 나오지 않음 | 不会出现等级B | 不會出現等級B |
| TRI-CIRCLE-CONTEST | 敵がいる間は進まない | No progress while enemies inside | Feind drin: stoppt | Ennemi dedans : bloqué | 적이 있는 동안 진행되지 않음 | 有敌人时不会推进 | 有敵人在內時不會推進 |
| TRI-CIRCLE-DEFEND | 味方がいる間は取られない | Can't be taken while allies inside | Verbündete drin: sicher | allié dedans : protégé | 아군이 있는 동안 빼앗기지 않음 | 有队友时不会被夺取 | 有隊友在內時不會被奪取 |
| TRI-CIRCLE-HEADCOUNT | 人数で速くならない | More players ≠ faster | mehr Spieler nicht schneller | Pas plus rapide à plusieurs | 인원이 많아도 빨라지지 않음 | 人数多也不会更快 | 人數多也不會更快 |
| TRI-CIRCLE-KEEP | 確定したサークルは離れてよい | Secured fields can be left | Gesicherter Zirkel darf verlassen werden | Cercle acquis : on peut le quitter | 점령이 확정된 원은 떠나도 됨 | 已占领的区域可以离开 | 已確定的圓環可以離開 |
| TRI-CIRCLE-OVERWRITE | 制圧までは他部隊のサークルも塗り替えられる | Until claimed, other teams' fields can be retaken | Bis zur Besetzung fremde Zirkel umfärbbar | Cercles adverses reprenables avant contrôle | 제압 전까지는 다른 부대의 원도 다시 점령할 수 있음 | 在控制战略目标点前，其他部队的占领区域也可重新占领 | 在壓制前，其他部隊的圓環也可被覆蓋 |
| TRI-CIRCLE-RESET | 確定する前に無人になると最初から | Emptied before secured: progress resets | Leer vor Sicherung → von vorn | Vidé avant acquisition : retour à zéro | 점령 확정 전에 아무도 없으면 처음부터 | 占领完成前若无人则从头开始 | 確定前若無人則從頭開始 |
| TRI-CLAIM-CONDITION | 戦略サークルを全部同じ部隊で占拠すると制圧 | Claimed when one team secures all fields of triumph | Alle Zirkel einer Fraktion → besetzt | Tous les cercles au même camp : Contrôlé | 전략 원을 모두 같은 부대가 점령하면 제압 | 同一部队占领全部占领区域即进入控制状态 | 以同一部隊佔領全部戰略圓環即可壓制 |
| TRI-CLAIM-LOCK | 制圧した目標地は奪われない | Claimed triumphs can't be taken | Besetzter Triumphpunkt nicht einnehmbar | Point contrôlé : imprenable | 제압한 목표지는 빼앗기지 않음 | 已控制的目标点不会被夺走 | 已壓制的目標地不會被奪走 |
| TRI-OBJ-RECIPIENT | 制圧した部隊だけに、制圧の間ずっと入る | Claiming team only, for the whole claim | Nur besetzende Fraktion, solange besetzt | Seul le camp qui contrôle gagne, tant que le point est Contrôlé | 제압한 부대에만, 제압 내내 계속 들어감 | 仅控制部队获得，整个控制期间持续 | 僅壓制部隊獲得，壓制期間持續獲得 |
| TRI-SNOW-BLESS-TIMING | 円が満ちたとき中にいると付く | Granted if inside when circle fills | Wer drin ist, wenn der Kreis voll ist | si dedans, cercle plein | 원이 가득 찰 때 안에 있으면 부여됨 | 圆环充满时若在其中即获得 | 圓圈填滿時在內即可獲得 |
| TRI-SNOW-STATUE-CENTER | 中央の三叉路が雪像でふさがる | Snow soldiers block central fork | Schneestatuen blockieren mittlere Gabelung | Un bonhomme de neige bloque le carrefour central | 중앙의 삼거리가 눈 조각상으로 막힘 | 中央三岔路被雪人堵住 | 中央的三叉路會被雪像堵住 |
| TRI-TIMEOUT | 時間切れは多い順 | At time limit: ranked by score | Zeitablauf: nach Punkten | Temps écoulé : classement par score | 시간 종료 시 점수 많은 순 | 时间结束时按数值高低排位 | 時間結束時按分數高低排位 |
