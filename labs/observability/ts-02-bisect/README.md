# ts-02-bisect: git bisect가 회귀 커밋을 몇 번 만에 찾는지 센다

트러블슈팅 실습-2의 코드입니다. 컨테이너 없이 git과 Python 3만 있으면 돌아갑니다.

## 무엇이 있나

| 파일 | 하는 일 |
|---|---|
| `make_repo.py` | 커밋 1,024개짜리 합성 저장소를 `git fast-import`로 만든다. 지정한 커밋에서 `src/pricing.py`의 반올림이나 할인율을 바꿔 회귀를 넣고, 지정한 커밋은 `src/BUILD`를 `broken`으로 만들어 시험 불가 상태를 흉내 낸다 |
| `check.py` | `git bisect run`이 부르는 시험. 1,999원 x 3개 + 부가세 10%가 6,597원이면 0(정상), 아니면 1(고장), 빌드가 깨졌으면 125. `FLAKE_P`·`FLAKE_MODE`로 시험을 일부러 흔든다 |
| `run_bisect.py` | 시나리오(single, linear, flaky, two, nonmono, skip)를 돌려 `out/`에 남긴다 |
| `flaky_wrong.py` | `out/flaky.tsv`에서 오답이 범인에서 얼마나 떨어져 있었는지 센다 |
| `config_bisect.py` | 설정 키 64개를 반분하는 시뮬레이션(git을 쓰지 않는다). 키 하나가 원인인 경우와 두 키가 함께 있어야 실패하는 경우 |

## 돌리는 법

```bash
cd labs/observability/ts-02-bisect
python3 run_bisect.py all        # 약 10분. 저장소는 work/ 아래에 생긴다(.gitignore)
python3 flaky_wrong.py           # 오답 위치 집계
python3 config_bisect.py         # 1초
```

시나리오 하나만: `python3 run_bisect.py flaky`. 결과는 `out/summary-<시나리오>.txt`, 실행마다 한 줄인 `out/<시나리오>.tsv`.

손으로 한 번 따라 하려면:

```bash
python3 make_repo.py work/demo --event 613:rounding=floor
cd work/demo
git bisect start main $(git rev-list --max-parents=0 main)
git bisect run python3 ../../check.py
git bisect reset
```

## 버전

git 2.54.0(Apple Git-157), Python 3.9.6, macOS(Apple M5 Pro). 시험이 흔들리는 실험은 `TRIAL`과 커밋 번호로 난수를 정해서 같은 명령이면 같은 결과가 나옵니다.

## 돌리다 만난 함정

- `check.py`를 저장소 안에 두면 bisect가 과거 커밋을 체크아웃할 때 스크립트도 바뀐다. 저장소 밖에 두고 절대 경로로 부른다
- 첫 번째 원인을 `git revert`로 되돌리려 하면 충돌한다. 커밋마다 `src/COMMIT_NO`가 바뀌기 때문이다. 실제 저장소에서도 회귀 커밋에 다른 변경이 섞여 있으면 같다. 그래서 `git show <커밋> -- src/pricing.py | git apply -R`로 해당 파일의 변경만 되돌렸다
- 처음에는 반올림 줄과 할인율 줄이 붙어 있어서, 커밋 300의 변경을 HEAD에서 거꾸로 적용할 때 패치 문맥이 커밋 700의 변경과 겹쳐 `git apply`가 실패했다. 두 줄을 파일 위아래로 떨어뜨렸다
- 깨진 빌드 비율이 높을 때 git은 건너뛴 커밋 근처에서 의사 난수로 다른 커밋을 고른다(`bisect.c`의 `skip_away`). 그래서 같은 비율이라도 어느 커밋이 깨졌느냐에 따라 단계 수가 달라진다. 비율마다 깨진 커밋 배치를 30가지로 바꿔 돌렸다
- 합성 커밋의 작성자 이메일을 바꿔(마스킹 검사에 걸려서 `<>`로 비웠다) 다시 돌렸더니, 커밋 해시가 바뀌면서 skip 시나리오의 건너뜀 횟수가 소수점 단위로 달라졌다(10% 기준 1.0 -> 0.9). 깨진 커밋 배치와 다른 시나리오의 결과는 그대로였다. 글의 숫자는 다시 돌린 쪽(`out/summary-all.txt`)이다
