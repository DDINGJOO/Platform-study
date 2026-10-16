# 불일치 변경이 있었던 묶음 40개, 손으로 본 판정 (v6.1.0 -> v6.2.0, 최소 100 토큰)

자료: `out/review/g<id>.txt` (scripts/dossier.py 가 만든 사본 위치와 -L 범위 안 diff). 판정 뒤의 근거는 커밋 메시지, 이슈, 끝 릴리스와 그 뒤(origin/main, 2026-10-16) 코드다.

판정 기준 (Juergens 외 2009 의 의도/비의도 구분을 이력으로 옮긴 것)

| 판정 | 뜻 |
|---|---|
| P | 같은 변경이 창 안에서 다른 사본에도 들어갔다. 괄호 안은 늦은 일수 |
| C | 동작 차이가 생기지 않았다. 이름·형식·주석·어노테이션만, 같은 날 되돌림, 다른 사본이 이미 같은 효과 |
| I | 한쪽에만 필요한 변경이다(API 가 다르다, 그 기능이 없다, 그 결함이 없다). 판단할 근거가 없으면 여기에 넣는다(원 논문의 보수적 규칙) |
| U | 다른 사본에도 필요했는데 빠졌다. 나중에 유지보수자가 같은 수정을 넣었거나 실행으로 결함을 확인한 것만 |
| U? | 코드를 읽으면 다른 사본에도 필요해 보이지만 확인하지 못했다. 집계에서는 I 로 센다 |

| 묶음 | 사본 (모듈 줄임) | 판정 | 근거 |
|---|---|---|---|
| 1 | webflux/webmvc RouterFunctionBuilder | P(0) | 같은 날 WebFlux 커밋과 WebMVC 커밋이 따로 |
| 6 | core OutputStreamPublisher / web http.client OutputStreamPublisher | P(190) | c531a8a705(2024-03-19) 가 core 사본에만 null 검사. 113b430fab(2024-09-25, gh-33592 "Align OutputStreamPublisher in core and web") 가 web 사본에 "Apply recent nullability changes" |
| 7 | jdbc / r2dbc NamedParameterUtils | P(2) | 2fc8b13dd5(gh-31944, 사용자 보고) 가 jdbc 만. 유지보수자가 이슈를 다시 열고 gh-32285 로 r2dbc 에 "for consistency with spring-jdbc" |
| 10 | webflux/webmvc VersionResourceResolver | C | 패턴 변수 이름 줄임만 |
| 14 | webflux/webmvc RouterFunctions | P(0) | 묶음 1 과 같은 짝 커밋. 1f6ab1a0c9 는 webmvc 쪽 줄바꿈만 |
| 17 | webflux/webmvc RequestMappingHandlerMapping | P(0) | 모듈별 null 안전성 커밋 둘(같은 날). 나머지 다섯 커밋은 양쪽을 한 번에 |
| 26 | ReactorNetty2 / Reactor ServerHttpResponse | I | Partitioned 쿠키: Netty 4 쪽은 구현, Netty 5 쪽은 "TODO: support Partitioned attribute when available in Netty 5 API" |
| 28 | webflux/webmvc ResourceChainRegistration | P(0) | 모듈별 NullAway 커밋 둘(같은 날) |
| 39 | Kotlin Serialization Binary/String Encoder | I | JSON 스트림 지원(gh-33428 등)은 문자열 형식에만 해당 |
| 48 | DefaultWebTestClient / DefaultWebClient | I | bodyValue(T, ParameterizedTypeReference) 추가. WebTestClient 인터페이스에는 그 메서드가 없다(origin/main 도 같다) |
| 61 | ReactorResourceFactory / ReactorNetty2ResourceFactory | I | 지연 시작은 Netty 4 쪽만. Netty 5 지원은 2025-02-11 e9d16da633 에서 통째로 제거 |
| 62 | webflux/webmvc RouterFunctions | P(0) | 묶음 1 과 같은 짝 커밋 |
| 70 | ServletWebRequest / DefaultServerWebExchange | C | 불일치는 eTag 이름 바꾸기 하나. 2024-09-10 두 사본 모두 ETag 유틸리티로 옮겨져 사라졌다(중복 제거) |
| 74 | webflux/webmvc RequestPredicates | C | 쓰이지 않는 메서드 삭제. webmvc 쪽에는 그 메서드가 없었다 |
| 75 | StompHeaders / HttpHeaders | I | headerSet 도입(대소문자 무시 반복)은 HttpHeaders 의 문제 |
| 88 | Kotlin Serialization Binary/String Decoder | I | DecodingException 처리: Binary 의 decode 는 스트림을 지원하지 않고(UnsupportedOperationException), decodeToMono 는 이미 처리하고 있었다 |
| 101 | HttpHeaders / WebSocketHttpHeaders | I | 묶음 75 와 같은 커밋 |
| 103 | StompHeaders / WebSocketHttpHeaders | P(0) | 모듈별 null 안전성 커밋 둘(같은 날) |
| 105 | DefaultWebTestClient / DefaultWebClient | I | defaultRequest 를 일찍 적용. WebTestClient 에는 defaultRequest 가 없다 |
| 107 | ReactorNettyClientRequestFactory / ReactorClientHttpConnector | I | 생명주기 정리 후 앞쪽 클래스가 새 이름으로 바뀌어(042346aa6a) 사본이 사라짐. 판단 근거 부족 |
| 108 | core/web OutputStreamPublisher | C | 정렬 커밋(gh-33592)이 양쪽을 같이 고침. web 쪽은 빈 줄만 |
| 113 | DefaultRestClient / DefaultWebClient | I | RestClient 에 쿠키 지원 추가. WebClient 에는 이미 있었다 |
| 124 | HttpHeaders / WebSocketHttpHeaders | **U** | 903493e9a9(2024-05-24) 가 asSingleValueMap() 위임을 HttpHeaders 와 ReadOnlyHttpHeaders 에만 넣었다. WebSocketHttpHeaders 는 자기 필드에 위임하므로 부모의 빈 맵을 돌려준다. 실행 확인: 6.2.0, 6.2.19 에서 `{}` (out/demo/headers.txt). 4593f877dd(2025-11-11, gh-35792) 가 "Overrides ... asSingleValueMap() ... in WebSocketHttpHeaders" |
| 126 | web / webflux SessionAttributesHandler | U? | 80949eb30f(gh-30463) 가 타입 기반 @SessionAttributes 의 이름을 세션에 저장(분산 세션). webflux 쪽은 origin/main 까지 메모리의 knownAttributeNames 만 본다. 실행하지 않았다 |
| 133 | webflux/webmvc RequestContext | C | webmvc 가 getMessageSource() 로. webflux 는 이미 this.messageSource |
| 139 | ReactorNettyClientRequestFactory / ReactorClientHttpConnector | I | 묶음 107 과 같다 |
| 145 | messaging AbstractExceptionHandlerMethodResolver / web ExceptionHandlerMethodResolver | I | @ExceptionHandler 의 내용 협상(미디어 타입)은 웹에만 |
| 153 | webflux/webmvc RequestContext | C | 묶음 133 과 같다 |
| 155 | MappingJackson2MessageConverter / AbstractJackson2HttpMessageConverter | P(1) | getMessage() null 검사, 모듈별 커밋(하루 차이) |
| 160 | webflux/webmvc DefaultServerResponseBuilder | C | webmvc 의 eTag 따옴표 처리를 HttpHeaders 로 넘김. webflux 는 이미 headers.setETag 만 불렀다 |
| 176 | FormHttpMessageReader / FormHttpMessageConverter | C | Map 지원을 넣었다가 5일 뒤 되돌림 |
| 182 | DefaultRestClientBuilder / DefaultWebClientBuilder | I | 묶음 113 과 같은 기능 |
| 185 | ReactorResourceFactory / ReactorNetty2ResourceFactory | C | isRunning() 을 필드 읽기로 |
| 186 | servlet / reactive DefaultServerRequestObservationConvention | I | gh-33725(상태 코드 0). reactive 쪽은 getStatusCode() 가 HttpStatusCode 를 돌려줘 같은 예외가 나지 않는다 |
| 210 | DefaultPartHttpMessageReader / PartEventHttpMessageReader | I | gh-32122 off-by-one. windowUntil 의 자르는 방식이 달라 DefaultPart 쪽에는 결함이 없다. 실행 확인(out/demo/maxparts.txt): 6.1.3 에서 부분 2개, maxParts=2 일 때 PartEvent 만 "Too many parts (3/2 allowed)" |
| 219 | DefaultResponseErrorHandler / StatusHandler | U? | 4972d18dd6(gh-28958) 가 RestTemplate 오류 메시지에 메서드와 URL 을 넣었다. RestClient 기본 처리기(StatusHandler)는 7.0.0 까지 그대로(out/demo/error-message.txt). PR 에서 기여자가 "consistent across WebClient, RestTemplate and RestClient?" 라고 물었으나 답은 없다. 결함인지는 판단하지 못했다 |
| 223 | messaging / web InvocableHandlerMethod | C | @Nullable 하나 |
| 226 | DefaultRestClient / DefaultWebClient | I | RestClient 에 요청 속성 추가. WebClient 에는 이미 있었다 |
| 233 | webflux/webmvc ParamsRequestCondition | C | 같은 날 넣고 되돌림 |
| 246 | http.client / reactive JdkClientHttpResponse | I | 본문 중복 구독 방지는 리액티브 쪽만 |

## 집계

| 판정 | 묶음 수 |
|---|---|
| P (창 안에서 따라 고쳐짐) | 9 (그중 0일 6, 1~2일 2, 190일 1) |
| C (동작 차이 없음) | 11 |
| I (한쪽만의 요구 또는 판단 불가) | 17 + U? 2 = 19 |
| U (빠진 것이 확인됨) | 1 |
| 합 | 40 |

창 안에서 코드가 바뀐 묶음(사본 2개 이상 남은 것) 79개(스크립트 출력 78 + 묶음 65 를 손으로 고침, README 참고) 중 불일치 변경이 한 번이라도 있었던 묶음 40개(51%).
P 9개는 변경 묶음으로 치면 다섯이다(묶음 1·14·62 가 한 기능의 짝 커밋, 17·28·103 이 모듈별 null 안전성 커밋).
비의도로 확인된 것은 1개(40개 중 2.5%), 확인 못 한 후보까지 넣으면 3개(7.5%).
