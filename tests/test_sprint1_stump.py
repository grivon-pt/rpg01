"""Спринт 1 «Шепчущий лес»: Древний пень (критерии 23–30) и автобой против него.

Запуск: timeout 150 python3 -u -I tests/test_sprint1_stump.py
Телефон 844×390 (dpr 2, touch). Каждый пункт печатает PASS / PART / FAIL.
"""
import sys, os, time, traceback
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa_common import *

R = Report('Спринт 1 «Шепчущий лес» — Древний пень')

SETUP = """(()=>{P.flags.stumpDown=0;P.flags.heartGot=0;if(curMap!=='forest')setMap('forest');for(const m of MAPS.forest.shrooms)m.alive=true;
  enemies.length=0;MAPS.forest.enemies=enemies;populate();enemies.splice(0,enemies.length,...enemies.filter(e=>e.boss));spawnT=999;
  placeHero(27,21);snapCam();P.grace=0;P.dead=0;texts.length=0;return 0})()"""

# журнал хода пня: номер хода, метки, корешки, перекус, позиции
INSTR = """(()=>{if(window._qaS)return 0;window._qaS=1;window.QS={ev:[],pos:[],exec:[]};
  const wrap=(n,f)=>{const o=window[n];window[n]=function(){f.apply(this,arguments);return o.apply(this,arguments)}};
  wrap('markCells',e=>QS.ev.push(['mark',e.t]));
  wrap('ftext',(x,y,t)=>{if(t==='Ой!')QS.oi=(QS.oi||0)+1});
  wrap('growRoots',e=>QS.ev.push(['grow',e.t,e.marks.map(m=>m.join(',')).join(' '),P.gx+','+P.gy]));
  wrap('stumpMunch',(e,m)=>QS.ev.push(['munch',e.t,Math.round(e.hp/e.max*100),cheb(m.x,m.y,e.gx,e.gy)]));
  wrap('execute',pv=>QS.exec.push(pv.kind+':'+(pv.target?pv.target.type:pv.id||'')));
  setInterval(()=>{const s=curMap==='forest'&&enemies.find(e=>e.boss&&e.hp>0);if(s&&combat)QS.pos.push([s.gx,s.gy]);
    for(const r of enemies)if(r.type==='root'&&r.hp>0){r._p=r._p||[r.gx,r.gy];if(r._p[0]!==r.gx||r._p[1]!==r.gy)QS.rootMoved=1}},30);return 0})()"""

OVERLAP = """(()=>{if(window._qaOv)return 0;window._qaOv=1;window.QAOV={n:0,ex:[]};
 const box=(s,cxp,cyp,fpx)=>{cx.save();cx.setTransform(1,0,0,1,0,0);cx.font='bold '+Math.round(fpx)+'px system-ui,sans-serif';const w=cx.measureText(s).width;cx.restore();return[cxp-w/2,cyp-fpx/2,cxp+w/2,cyp+fpx/2]};
 const hit=(a,b)=>a[0]<b[2]&&b[0]<a[2]&&a[1]<b[3]&&b[1]<a[3];
 setInterval(()=>{if(!combat)return;const a=combat.active;const hud=[];
   if(a)hud.push([a===P?'Твой ход':'Ходит '+a.name,box(a===P?'Твой ход':'Ходит '+a.name,UW/2*H,25*H,5.5*H)]);
   if(auto)hud.push(['АВТОБОЙ',box('АВТОБОЙ',UW/2*H,33*H,4.4*H)]);
   for(const t of texts){if(t.life/t.max<.3)continue;const b=box(t.s,wx(t.x)*S,wy(t.y)*S,t.size*H*1.1);
     for(const[hn,hb]of hud)if(hit(b,hb)){QAOV.n++;if(!QAOV.ex.includes(t.s+' × '+hn))QAOV.ex.push(t.s+' × '+hn)}}},40);return 0})()"""


def safe(key):
    def deco(fn):
        def run(*a):
            try:
                fn(*a)
            except Exception as e:
                R.check(key, False, 'исключение: ' + repr(e)[:200]); traceback.print_exc(limit=2)
        return run
    return deco


def hero_turn(g, t=8):
    return g.wait("combat&&combat.active===P&&!busy", t)


@safe('23. Пень спит («z»), сам не нападает; шаг на (28,21) будит: реплика и бой')
def c23_26(pw, srv, errs):
    g = Game(pw, srv.url, errs=errs); g.new_game(); g.strong_hero(); g.ev(INSTR)
    g.ev(SETUP); g.ev("placeHero(26,20);snapCam();0")
    z = g.wait("texts.some(t=>t.s==='z')", 4); asleep = g.ev("stumpOf().asleep"); no_fight = not g.ev("!!combat")
    g.ev("placeHero(27,21);0"); time.sleep(1.0)  # у самого прохода, но вне логова
    no_fight2 = not g.ev("!!combat")
    g.ev("placeHero(27,21);texts.length=0;window.QB=new Set();window._qb=setInterval(()=>{if(banner)QB.add(banner.s)},5);0"); g.walk_to(28, 21)
    woke = g.wait("!!combat", 3); time.sleep(1.5)
    banners = g.ev("clearInterval(window._qb),[...QB]")
    t = g.texts(); b = g.ev("banner&&banner.s")
    R.check('23. Пень спит («z»), сам не нападает; шаг на (28,21) будит: реплика и бой',
            z and asleep and no_fight and no_fight2 and woke and 'Кто топчет мой мох?! Я спал сто лет!' in t and not g.ev("stumpOf().asleep"),
            f'«z»={z}, спит={asleep}, боя нет рядом с логовом={no_fight and no_fight2}; после шага бой={woke}, баннер «{b}», реплика={"Кто топчет" in t}')
    R.check('23б. Баннер «Древний пень проснулся!» виден при входе в логово', 'Древний пень проснулся!' in banners,
            f'баннеры за 1,5 с после шага на (28,21): {banners} — «Бой!» из startCombat сразу перезаписывает баннер пробуждения')
    # 24–26: герой стоит в логове и просто заканчивает ход; смотрим 9 ходов пня
    g.ev("P.hp=99999;P.st.end=10;QS.ev=[];QS.pos=[];0")
    g.fast(True, 2)
    for i in range(10):
        hero_turn(g, 10)
        # уводим героя с меток (кроме одного раза — проверка «Ой!»)
        if not g.ev("!!window._onMark"):
            g.ev("(()=>{const s=stumpOf();if(s.marks.length){placeHero(s.marks[0][0],s.marks[0][1]);window._onMark=1;texts.length=0}return 0})()")
        g.ev("endHeroTurn();0"); time.sleep(.1)
    hero_turn(g, 10); g.fast(False)
    ev = g.ev("QS.ev"); pos = g.ev("QS.pos")
    marks = [e[1] for e in ev if e[0] == 'mark']; grows = [e for e in ev if e[0] == 'grow']
    marks_ok = marks and all(t % 3 == 2 for t in marks); grows_ok = grows and all(e[1] % 3 == 0 for e in grows)
    lair = g.ev("l=>l.every(([x,y])=>dE(x,y,LAIR)<1)", pos)
    oi = any(e[3] in e[2].split(' ') for e in grows) and g.ev("QS.oi>0")
    roots = g.ev("enemies.filter(e=>e.type==='root'&&e.hp>0).length")
    max_roots_ok = g.ev("enemies.filter(e=>e.type==='root').length<=3")
    R.check('24. Пень не выходит за пределы логова', lair and len(pos) > 20, f'позиций пня в бою: {len(pos)}, все в логове={lair}')
    R.check('25. Метки на ходах 2,5,8…, корешки на 3,6,9…, не больше 3; на метке — «Ой!» и урон, корешок не растёт',
            marks_ok and grows_ok and max_roots_ok and oi,
            f'метки на ходах {marks}, рост на ходах {[e[1] for e in grows]}, живых корешков {roots}, герой стоял на метке при росте={oi}')
    # 26. корешки не двигаются, бьют только соседа; исчезают по концу боя
    moved = g.ev("!!QS.rootMoved")
    g.ev("(()=>{const r=enemies.filter(e=>e.type==='root'&&e.hp>0);window._rc=r.length;return 0})()")
    g.ev("placeHero(27,21);0")
    attacks_far = g.ev("""(()=>{let bad=0;const ea=window.enemyAttack;window.enemyAttack=function(e){if(e.type==='root'&&distE(P,e)>1)bad++;return ea.apply(this,arguments)};window._bad=()=>bad;return 0})()""")
    for i in range(3):
        hero_turn(g, 10); g.ev("endHeroTurn();0"); time.sleep(.1)
    hero_turn(g, 10)
    bad = g.ev("window._bad()")
    rc = g.ev("window._rc")
    g.ev("endCombat(false);0"); time.sleep(.2)
    gone = g.ev("enemies.filter(e=>e.type==='root'&&e.hp>0).length")
    R.check('26. Корешки не двигаются, бьют только соседа; исчезают, когда бой кончается', rc > 0 and not moved and bad == 0 and gone == 0,
            f'корешков было {rc}, сдвинулись={moved}, ударов не по соседу {bad}, после конца боя осталось {gone}')
    g.close()


@safe('27. Пень ест гриб в радиусе 4 при ХП ≤ 50% (+26), не чаще раза в 2 хода, не больше 4')
def c27_28(pw, srv, errs):
    g = Game(pw, srv.url, errs=errs); g.new_game(); g.strong_hero(); g.ev(INSTR)
    g.ev(SETUP); g.walk_to(28, 21); hero_turn(g)
    g.ev("P.hp=99999;QS.ev=[];0")
    hp_seen = []
    g.fast(True, 2)
    for i in range(14):
        hero_turn(g, 10)
        g.ev("(()=>{const s=stumpOf();if(s&&s.hp>40)s.hp=Math.min(s.hp,60);return 0})()")
        hp_seen.append(g.ev("stumpOf()&&stumpOf().hp"))
        g.ev("endHeroTurn();0"); time.sleep(.05)
    hero_turn(g, 10); g.fast(False)
    m = [e for e in g.ev("QS.ev") if e[0] == 'munch']
    left = g.ev("MAPS.forest.shrooms.filter(s=>s.alive).length")
    gap_ok = all(b[1] - a[1] >= 2 for a, b in zip(m, m[1:]))
    R.check('27. Пень ест гриб в радиусе 4 при ХП ≤ 50% (+26), не чаще раза в 2 хода, не больше 4',
            3 <= len(m) <= 4 and gap_ok and all(x[2] <= 50 and x[3] <= 4 for x in m) and len(m) + left == 4,
            f'перекусы [ход, ХП% до, расстояние до гриба]: {[x[1:] for x in m]}, грибов осталось {left} (дальше 4 клеток от пня)')
    # «+26»
    g.ev("endCombat(false);0"); g.ev(SETUP); g.walk_to(28, 21); hero_turn(g)
    g.ev("(()=>{const s=stumpOf();s.hp=50;s.munchCd=0;texts.length=0;return 0})()")
    g.ev("endHeroTurn();0"); hero_turn(g, 10)
    heal = g.ev("[stumpOf().hp,texts.map(t=>t.s).filter(s=>s.startsWith('+')||s.startsWith('Ням'))]")
    # 28. сорвать гриб в бою
    g.ev("(()=>{for(const m of MAPS.forest.shrooms)m.alive=true;placeHero(29,20);mode='melee';return 0})()")
    pv = g.ev("(()=>{const pv=makePreview(30,19);return[pv.kind,pv.cost,pv.ok]})()")
    n0, ap0 = g.ev("[bagCount('forest_mush'),P.ap]")
    # тап как игрок: первый тап — подсказка, второй — действие
    g.tap_cell(30, 19, dy=-6); time.sleep(.2)
    label = g.ev("preview&&preview.kind==='pick'?'сорвать · '+preview.cost+' ОД':''")
    g.tap_cell(30, 19, dy=-6); time.sleep(.6)
    n1, ap1, alive = g.ev("[bagCount('forest_mush'),P.ap,MAPS.forest.shrooms.find(m=>m.x===30&&m.y===19).alive]")
    R.check('28. Сорвать гриб-боровик в бою: 2 ОД, «сорвать · 2 ОД», в сумку «Лесной гриб»',
            pv == ['pick', 2, True] and label == 'сорвать · 2 ОД' and n1 == n0 + 1 and ap0 - ap1 == 2 and not alive,
            f'подсказка {pv} «{label}», ОД {ap0}→{ap1}, грибов в сумке {n0}→{n1}; лечение пня: ХП 50 → {heal[0]}, надписи {heal[1]}')
    g.ev("endCombat(false);0"); g.close()


@safe('29. Победа: пень спит на месте, добыча, опыт; после перезагрузки спит')
def c29_30(pw, srv, errs):
    g = Game(pw, srv.url, errs=errs); g.new_game(); g.strong_hero(); g.ev(INSTR)
    # 30а. уход дальше 12 клеток
    g.ev(SETUP); g.walk_to(28, 21); hero_turn(g)
    g.ev("stumpOf().hp=40;P.hp=99999;0")
    for i in range(3):
        hero_turn(g, 10); g.ev("endHeroTurn();0"); time.sleep(.1)
    hero_turn(g, 10)
    r_before = g.ev("enemies.filter(e=>e.type==='root'&&e.hp>0).length")
    g.ev("placeHero(12,13);snapCam();texts.length=0;endHeroTurn();0")
    g.wait("!combat", 6); time.sleep(.3)
    flee = g.ev("(()=>{const s=enemies.find(e=>e.boss);return[!!combat,s.hp,s.max,s.asleep,enemies.filter(e=>e.type==='root'&&e.hp>0).length,texts.some(t=>t.s==='Пень снова задремал')]})()")
    # 30б. поражение
    g.ev(SETUP); g.walk_to(28, 21); hero_turn(g)
    g.ev("stumpOf().hp=30;P.coins=40;P.hp=1;hurtHero(stumpOf(),50);0")
    g.wait("P.dead<=0&&!combat", 6); time.sleep(.3)
    lost = g.ev("[curMap,P.coins,MAPS.forest.enemies.filter(e=>e.boss).map(e=>[e.hp,e.asleep]),MAPS.forest.enemies.filter(e=>e.type==='root').length]")
    g.ev("setMap('forest');0"); sh = g.ev("MAPS.forest.shrooms.every(m=>m.alive)")
    R.check('30. Уход дальше 12 клеток или поражение → у пня снова полные ХП, корешков нет',
            flee[0] is False and flee[1] == flee[2] and flee[3] and flee[4] == 0 and lost[0] == 'meadow' and lost[1] == 30 and lost[2] == [[130, True]] and lost[3] == 0 and sh,
            f'уход: [бой,ХП,макс,спит,корешки,«Пень снова задремал»]={flee} (корешков до ухода {r_before}); поражение: {lost}, грибы снова на месте={sh}')
    # 29. победа
    g.ev(SETUP + ";addItem('forest_mush',0,true)")
    g.walk_to(28, 21); hero_turn(g)
    g.ev("P.lvl=99;P.xp=0;0")
    xpneed = g.ev("Math.round(70*D.xpMul())")
    hero_turn(g, 10)
    g.ev("(()=>{const s=stumpOf();s.hp=1;s.ac=-999;s.def=0;items.length=0;texts.length=0;mode='melee';P.bag=[];placeHero(s.gx-1,s.gy);P.ap=D.maxAp();execute(makePreview(s.gx,s.gy));return 0})()")
    g.wait("!combat&&!!P.flags.stumpDown", 6)
    lines = set()
    for _ in range(40):
        lines |= set(g.ev("texts.map(t=>t.s)")); time.sleep(.1)
    drops = g.ev("items.filter(i=>i.kind!=='coin').map(i=>i.kind==='item'?i.id+'×'+i.qty:i.kind).concat(P.bag.map(b=>b.id+'×'+b.qty)).sort()")
    xpgot = g.ev("P.xp")
    coins = g.ev("items.filter(i=>i.kind==='coin').length")
    st = g.ev("[P.flags.stumpDown,P.flags.stumpAt,enemies.some(e=>e.boss&&e.hp>0),walkable(...P.flags.stumpAt)]")
    g.ev("texts.length=0;tapCell(...P.flags.stumpAt,true);0"); time.sleep(.1); hrr = 'Хрр… хрр…' in g.texts()
    g.ev("placeHero(27,21);0")
    g.fast(True, 2); time.sleep(1.5); g.fast(False)  # подобрать добычу не обязательно
    g.ev("save();0"); g.reload_continue()
    g.ev("placeHero(28,21);P.grace=0;0"); g.walk_to(30, 21); time.sleep(1)
    after = g.ev("[curMap,P.flags.stumpDown,!!combat,enemies.some(e=>e.boss&&e.hp>0),walkable(...P.flags.stumpAt)]")
    need_lines = {'Туман… с башни… разбудил…', 'Зевну…', 'посплю…'}
    R.check('29. Победа: пень спит на месте, добыча, опыт; после перезагрузки спит',
            st[0] == 1 and not st[2] and st[3] is False and hrr and 'heart_forest×1' in drops and 'forest_mush×3' in drops and 'pot_hp×1' in drops and 'heart' in drops
            and need_lines <= lines and xpgot == xpneed and after == ['forest', 1, False, False, False],
            f'флаг и место {st[:2]}, пень-декорация непроходима={st[3] is False}, «Хрр… хрр…»={hrr}; добыча (на земле и подобранная) {drops}, монет {coins}, опыт +{xpgot} (70×множитель={xpneed}); реплики {sorted(need_lines & lines)}; после перезагрузки [карта,флаг,бой,живой пень,проходим]={after}')
    g.close()


@safe('Автобой против пня')
def auto_vs_stump(pw, srv, errs):
    g = Game(pw, srv.url, errs=errs); g.new_game(); g.ev(INSTR); g.ev(OVERLAP)
    runs = []
    shot = False
    for trial in range(3):
        g.ev("P.lvl=4;P.xp=0;0"); g.strong_hero()
        g.ev(SETUP); g.ev("P.bag=[];addItem('pot_hp',2,true);QS.exec=[];QS.ev=[];combatTip=0;tipShown=true;auto=true;0")
        g.fast(True, 3); g.walk_to(28, 21); g.wait("!!combat", 3)
        rounds = 0; t0 = time.time()
        while g.ev("!!combat") and time.time() - t0 < 60:
            rounds = max(rounds, g.ev("combat?combat.round:0"))
            if not shot and g.ev("QAOV.n>0"):
                g.fast(False); g.shot('/tmp/qa_stump_text_over_autoboy.png'); shot = True; g.fast(True, 3)
            time.sleep(.05)
        g.fast(False)
        ex = Counter(g.ev("QS.exec")); mun = len([e for e in g.ev("QS.ev") if e[0] == 'munch'])
        won = g.ev("!!P.flags.stumpDown")
        runs.append((won, rounds, ex.get('melee:root', 0), ex.get('melee:stump', 0) + ex.get('bow:stump', 0) + ex.get('spell:stump', 0), ex.get('pick:', 0), mun))
        g.ev("P.dead=0;0"); time.sleep(.3)
    ov = g.ev("QAOV.ex")
    allwin = all(r[0] for r in runs); picks = sum(r[4] for r in runs)
    roots = sum(r[2] for r in runs); total = sum(r[2] + r[3] for r in runs)
    # после исправлений (b721f0e) автобой бьёт пня, а не корешки, и срывает ближние грибы
    ok_ai = picks > 0 and roots <= total * .2
    R.check('Автобой против пня: побеждает эталоном; бьёт пня и срывает грибы', True if allwin and ok_ai else ('part' if allwin else False),
            f'[победа, раундов, ударов по корешкам, по пню, сорвано грибов, перекусов пня] = {runs}; по корешкам {roots}/{total} действий; сорвано грибов {picks}; раундов {min(r[1] for r in runs)}–{max(r[1] for r in runs)} (дизайн 6–9)')
    R.check('Надписи над пнём не налезают на «Твой ход»/«Ходит …»/«АВТОБОЙ»', not ov, f'наложения: {ov[:6]} (скриншот /tmp/qa_stump_text_over_autoboy.png)')
    g.close()


def main(pw, srv, errs):
    t0 = time.time()
    for f in (c23_26, c27_28, c29_30, auto_vs_stump):
        f(pw, srv, errs)
    R.check('Ошибок в консоли нет', not errs, str(errs[:3]))
    R.summary(); print(f'время {time.time()-t0:.0f} с')


if __name__ == '__main__':
    run(main)
