# Week 11 실습

## 오늘 한 것
- PyInstaller 설치 및 빌드
- `resource_path()` 함수 추가
- `--add-data` 옵션으로 에셋 포함
- `.exe` 실행 확인

---

## resource_path() 를 써야 하는 이유

PyInstaller로 프로그램을 빌드하면 실행 파일 내부에 이미지, 사운드 등의 리소스 파일이 함께 포함된다.  
하지만 `.py` 파일로 실행할 때와 `.exe` 파일로 실행할 때의 기준 경로가 달라지기 때문에 기존 상대 경로만으로는 파일을 찾지 못하는 문제가 발생할 수 있다.

`resource_path()` 함수는 현재 실행 환경에 맞는 실제 리소스 경로를 반환해 주므로,
개발 환경과 배포 환경 모두에서 동일하게 리소스 파일을 불러올 수 있도록 도와준다.

예시 코드

(python)

import os
import sys

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(__file__)
    return os.path.join(base, relative_path)

image_path = resource_path("assets/image.png")

## 빌드 명령어
- 기본
pyinstaller --onefile game.py

- 터미널 창 숨기기 (배포용)
pyinstaller --onefile --windowed game.py

- 에셋 포함 + 이름 지정
pyinstaller --onefile --windowed --add-data "assets;assets" --name=MyGame game.py

--add-data "A;B
A: 내 PC 폴더, B: .exe 안에서의 위치

폴더가 여러 개라면 반복 사용
pyinstaller --onefile --windowed ^
            --add-data "assets;assets" ^
            --add-data "fonts;fonts" ^
            --add-data "sounds;sounds" ^
            --name=MyGame game.py

## .spec

옵션이 길어지면 .spec 파일로 관리할수 있음.
# game.spec 에서 datas 부분만 수정
a = Analysis( ['game.py'],
    datas = [
        ('assets' , 'assets'),
        ('fonts' , 'fonts'),
        ('sounds' , 'sounds'),
    ],
    hiddenimports = [],

    ...
)

# 이후 재빌드는 한 줄로
pyinstaller game.spe

## AI 활용 내역
# Q1: resource_path 코드 설명해줘
- AI답변: sys를 통해 현제 py로 실행중인지 .exe로 실행중인지를 확인하고 그에 따라 맞춤으로 파일경로를 반환해줌.

# Q2: --add-data에 여러번 사용에 대해 추가 설명을 요청
- --add-data 옵션은 실행 파일에 필요한 폴더(assets, fonts, sounds 등)를 함께 포함시키기 위해 여러 번 반복해서 사용하는 것이다.