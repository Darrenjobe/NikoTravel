import SwiftUI

struct HistoryListView: View {
    @State private var conversations: [Conversation] = []
    @State private var filter = "all"
    @State private var isLoading = false

    var body: some View {
        VStack(spacing: 0) {
            Picker("Filter", selection: $filter) {
                Text("All").tag("all")
                Text("Ask").tag("ask")
                Text("Journal").tag("journal")
            }
            .pickerStyle(.segmented)
            .padding()

            List {
                ForEach(conversations) { convo in
                    NavigationLink {
                        ConversationThreadView(conversation: convo)
                    } label: {
                        ConversationRow(conversation: convo)
                    }
                }
                if conversations.isEmpty && !isLoading {
                    Text("No conversations yet — ask Niko something or journal a place.")
                        .font(.footnote).foregroundStyle(.secondary)
                }
            }
            .scrollContentBackground(.hidden)
            .background(Color.hodPaper)
        }
        .task(id: filter) { await load() }
    }

    private func load() async {
        isLoading = true
        defer { isLoading = false }
        let type = filter == "all" ? nil : filter
        if let response = try? await APIClient.shared.conversations(type: type) {
            conversations = response.conversations
        }
    }
}

private struct ConversationRow: View {
    let conversation: Conversation

    private var isAsk: Bool { conversation.type == "ask" }
    private var accent: Color { isAsk ? .hodAegean : .hodTerra }
    private var icon: String { isAsk ? "bubble.left.fill" : "square.and.pencil" }

    private var formattedDate: String {
        let date = Date(timeIntervalSince1970: conversation.startedAt)
        let f = DateFormatter()
        f.dateStyle = .medium
        f.timeStyle = .short
        return f.string(from: date)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            HStack(alignment: .top, spacing: 8) {
                Image(systemName: icon)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(accent)
                    .padding(.top, 2)
                Text(conversation.summary)
                    .font(.subheadline.weight(.medium))
                    .foregroundStyle(Color.hodInk)
                    .lineLimit(2)
            }
            HStack {
                if let place = conversation.placeName {
                    Text(place)
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(Color.hodTerra)
                }
                Spacer()
                Text(formattedDate)
                    .font(.hodMeta(.caption2))
                    .foregroundStyle(Color.hodMuted)
            }
        }
        .padding(.vertical, 2)
    }
}

struct ConversationThreadView: View {
    let conversation: Conversation
    @State private var detail: ConversationDetail?

    private var accent: Color { conversation.type == "ask" ? .hodAegean : .hodTerra }

    var body: some View {
        Group {
            if let detail {
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 10) {
                        ForEach(detail.messages.indices, id: \.self) { i in
                            HistoryBubble(
                                text: detail.messages[i].text,
                                isUser: detail.messages[i].role == "user",
                                accent: accent
                            )
                        }
                    }
                    .padding()
                }
            } else {
                ProgressView()
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
        .background(Color.hodPaper)
        .tint(accent)
        .navigationTitle(conversation.summary)
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
    }

    private func load() async {
        detail = try? await APIClient.shared.conversation(id: conversation.id)
    }
}
