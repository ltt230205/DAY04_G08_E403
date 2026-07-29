# Demo v0 - v1 - v2

File này dùng để demo quá trình tối ưu agent bằng log thật.

## Tóm tắt nhanh

| Version | Run cần mở | Sửa gì / ý nghĩa | Kết quả |
|---|---|---|---|
| v0 | `runs/v0_B_base_openrouter_20260729T163049014196.json` | Baseline: prompt/tool còn mơ hồ, agent hay đoán thiếu thông tin và tự gửi. | 14/20, accuracy 0.70 |
| v1 | `runs/v1_B_base_openrouter_20260729T154044120855.json` | Sửa bước đầu về routing/argument cho lookup news, nhưng boundary và missing-info vẫn chưa tốt. | 15/20, accuracy 0.75 |
| v2 | `runs/v2_B_base_openrouter_20260729T163343508526.json` | Sửa rõ prompt + tool declaration: hỏi lại khi thiếu thông tin, xác nhận trước khi send, không gọi tool ngoài scope, cấm social_search query rỗng. | 20/20, accuracy 1.00 |

## Câu mở đầu demo

"Nhóm em demo bằng run JSON thật. Mỗi version đều chạy bằng OpenRouter để tránh lỗi quota của Gemini. Tụi em nhìn failures trong log, sửa prompt/tool declaration, rồi chạy lại để đo metric."

## v0 - Baseline

Mở file:

```text
runs/v0_B_base_openrouter_20260729T163049014196.json
```

Chỉ vào phần:

```text
summary.total_cases = 20
summary.measured_cases = 20
summary.provider_error_cases = 0
summary.passed_cases = 14
summary.case_accuracy = 0.7
summary.tool_routing_accuracy = 0.8
summary.argument_accuracy = 0.7
summary.multiturn_accuracy = 1.0
```

Nói:

"Đây là baseline hợp lệ bằng OpenRouter, không có provider error. Agent pass 14/20. Các lỗi chính là sai query news, gọi tool cho câu ngoài phạm vi, không hỏi lại khi thiếu handle/URL, và tự gọi send thay vì hỏi xác nhận."

Các case fail để mở/chỉ:

```text
R03_web_news_routing
R08_out_of_scope
R10_missing_handle
R11_missing_url
R12_confirm_before_send
R13_parallel_web_and_tweets
```

Ý nghĩa từng lỗi:

```text
R03: query expected "AI", got "AI news"
R08: đáng ra không gọi tool nhưng agent vẫn gọi tool
R10: thiếu account tweet, đáng ra clarify nhưng gọi timeline
R11: thiếu URL, đáng ra clarify nhưng gọi fetch
R12: gửi Telegram, đáng ra clarify yes_no nhưng gọi send
R13: request cần web + Twitter, lookup args bị sai
```

## v1 - Sửa bước đầu

Mở file:

```text
runs/v1_B_base_openrouter_20260729T154044120855.json
```

Chỉ vào:

```text
summary.total_cases = 20
summary.measured_cases = 20
summary.provider_error_cases = 0
summary.passed_cases = 15
summary.case_accuracy = 0.75
summary.tool_routing_accuracy = 0.75
summary.argument_accuracy = 0.75
summary.multiturn_accuracy = 1.0
```

Nói:

"Sau lần sửa đầu, accuracy tăng từ 0.70 lên 0.75. Một số lỗi argument/routing news được cải thiện, nhưng các lỗi quan trọng vẫn còn: out-of-scope vẫn gọi tool, thiếu handle/URL vẫn không clarify, và send vẫn chưa qua confirmation."

Các case còn fail:

```text
R08_out_of_scope
R10_missing_handle
R11_missing_url
R12_confirm_before_send
R14_out_of_scope_coding
```

Điểm rút ra:

"v1 chưa đủ tốt. Log cho thấy cần sửa thẳng vào boundary: khi nào không dùng tool, khi nào bắt buộc hỏi lại, và khi nào bắt buộc xác nhận."

## v2 - Final fix cho base eval

Mở file:

```text
runs/v2_B_base_openrouter_20260729T163343508526.json
```

Chỉ vào:

```text
summary.total_cases = 20
summary.measured_cases = 20
summary.provider_error_cases = 0
summary.passed_cases = 20
summary.case_accuracy = 1.0
summary.tool_routing_accuracy = 1.0
summary.argument_accuracy = 1.0
summary.multiturn_accuracy = 1.0
summary.failure_counts = {}
summary.observed_mismatch_counts = {}
```

Nói:

"Ở v2, nhóm sửa rõ system prompt và tools.yaml. Prompt quy định theo thứ tự ưu tiên: external action phải clarify yes_no trước, thiếu handle/URL phải clarify, ngoài scope thì không gọi tool, câu hỏi capability thì trả lời trực tiếp. Tool declaration cũng làm rõ send là side effect, fetch không được dùng nếu thiếu URL, timeline cần account, social_search không được query rỗng."

Các thay đổi chính cần nói:

```text
1. Gửi/post/publish: luôn gọi clarify response_type=yes_no trước, không gọi send ngay.
2. Thiếu account tweet hoặc thiếu URL: gọi clarify response_type=text.
3. Out-of-scope như toán, code, dịch thuật: không gọi tool.
4. social_search bắt buộc có query không rỗng.
5. lookup news giữ query ngắn: "Tin AI hôm nay" -> query="AI", topic="news", timeframe="day".
6. Multi-turn chỉ xử lý latest turn, dùng earlier turns làm context.
```

## Câu kết demo

"Như vậy evidence từ log cho thấy quá trình cải thiện rõ: v0 đạt 70%, v1 đạt 75%, và v2 đạt 100%. Nhóm không sửa theo cảm giác mà đọc failure trong JSON, sửa prompt/tool declaration, rồi chạy lại để đo metric."

## Nếu giảng viên hỏi vì sao có Gemini logs

Trả lời:

"Ban đầu nhóm có thử Gemini nhưng bị quota 429 nên không dùng làm metric chính. Metric demo chính dùng OpenRouter vì provider_error_cases bằng 0 ở cả v0, v1, v2."
